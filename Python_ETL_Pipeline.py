import findspark
findspark.init()
from pyspark.sql import SparkSession
import os
import time
import datetime
from uuid import *
from pyspark.sql.functions import *
from pyspark.sql.types import *
import time_uuid 


spark = SparkSession.builder.appName("CassandraToMySQLDataPipeline") \
    .config("spark.cassandra.connection.host", "cassandra") \
    .config("spark.cassandra.connection.port", "9042") \
    .getOrCreate()



def get_mysql_latest_time(url,driver,user,password):  
    """Retrieves the latest 'updated_at' timestamp from the MySQL 'events' table."""

    sql = """(select max(updated_at) from events) data"""
    mysql_time = spark.read.format('jdbc').options(url=url, driver=driver, dbtable=sql, user=user, password=password).load()
    mysql_time = mysql_time.take(1)[0][0]

    if mysql_time is None:
        mysql_latest = '1998-01-01 23:59:59'
    else :
        mysql_latest = mysql_time.strftime('%Y-%m-%d %H:%M:%S')

    return mysql_latest 




def get_latest_time_cassandra():
    data = spark.read.format("org.apache.spark.sql.cassandra").options(table = 'tracking',keyspace = 'realtime_data').load()
    cassandra_latest_time = data.agg({'ts':'max'}).take(1)[0][0]
    return cassandra_latest_time



    
def calculating_clicks(df):
    """Calculate numbers of clicks for each group of job_id, date, hour, publisher_id, campaign_id, group_id"""
    
    clicks_data = df.filter(df.custom_track == 'click')
    clicks_data = clicks_data.na.fill({'bid':0})
    clicks_data = clicks_data.na.fill({'job_id':0})
    clicks_data = clicks_data.na.fill({'publisher_id':0})
    clicks_data = clicks_data.na.fill({'group_id':0})
    clicks_data = clicks_data.na.fill({'campaign_id':0})

    clicks_data.registerTempTable('clicks')
    clicks_output = spark.sql("""select job_id , date(ts) as date , hour(ts) as hour , publisher_id , campaign_id , group_id , avg(bid) as bid_set, count(*) as clicks , sum(bid) as spend_hour from clicks
    group by job_id , date(ts) , hour(ts) , publisher_id , campaign_id , group_id """)

    return clicks_output 
    


def calculating_conversion(df):
    """Calculate numbers of conversion for each group of job_id, date, hour, publisher_id, campaign_id, group_id"""

    conversion_data = df.filter(df.custom_track == 'conversion')
    conversion_data = conversion_data.na.fill({'job_id':0})
    conversion_data = conversion_data.na.fill({'publisher_id':0})
    conversion_data = conversion_data.na.fill({'group_id':0})
    conversion_data = conversion_data.na.fill({'campaign_id':0})

    conversion_data.registerTempTable('conversion')
    conversion_output = spark.sql("""select job_id , date(ts) as date , hour(ts) as hour , publisher_id , campaign_id , group_id , count(*) as conversions  from conversion
    group by job_id , date(ts) , hour(ts) , publisher_id , campaign_id , group_id """)

    return conversion_output 

    

def calculating_qualified(df):    
    """Calculate numbers of qualified application for each group of job_id, date, hour, publisher_id, campaign_id, group_id"""

    qualified_data = df.filter(df.custom_track == 'qualified')
    qualified_data = qualified_data.na.fill({'job_id':0})
    qualified_data = qualified_data.na.fill({'publisher_id':0})
    qualified_data = qualified_data.na.fill({'group_id':0})
    qualified_data = qualified_data.na.fill({'campaign_id':0})
    qualified_data.registerTempTable('qualified')

    qualified_output = spark.sql("""select job_id , date(ts) as date , hour(ts) as hour , publisher_id , campaign_id , group_id , count(*) as qualified  from qualified
    group by job_id , date(ts) , hour(ts) , publisher_id , campaign_id , group_id """)

    return qualified_output
    


def calculating_unqualified(df):
    """Calculate numbers of unqualified application for each group of job_id, date, hour, publisher_id, campaign_id, group_id"""

    unqualified_data = df.filter(df.custom_track == 'unqualified')
    unqualified_data = unqualified_data.na.fill({'job_id':0})
    unqualified_data = unqualified_data.na.fill({'publisher_id':0})
    unqualified_data = unqualified_data.na.fill({'group_id':0})
    unqualified_data = unqualified_data.na.fill({'campaign_id':0})

    unqualified_data.registerTempTable('unqualified')
    unqualified_output = spark.sql("""select job_id , date(ts) as date , hour(ts) as hour , publisher_id , campaign_id , group_id , count(*) as unqualified  from unqualified
    group by job_id , date(ts) , hour(ts) , publisher_id , campaign_id , group_id """)

    return unqualified_output
    


def process_final_data(clicks_output,conversion_output,qualified_output,unqualified_output):
    final_data = clicks_output.join(conversion_output,['job_id','date','hour','publisher_id','campaign_id','group_id'],'full').\
    join(qualified_output,['job_id','date','hour','publisher_id','campaign_id','group_id'],'full').\
    join(unqualified_output,['job_id','date','hour','publisher_id','campaign_id','group_id'],'full')
    return final_data 
    


def retrieve_company_data(url,driver,user,password):
    sql = """(SELECT id as job_id, company_id, group_id, campaign_id FROM job) test"""
    company = spark.read.format('jdbc').options(url=url, driver=driver, dbtable=sql, user=user, password=password).load()
    return company 
    


def import_to_mysql(output, url, driver, user, password):
    output.write.format("jdbc") \
    .options(url=url, driver=driver, user=user, password=password) \
    .option("dbtable", "events") \
    .mode("append") \
    .option("spark.sql.sources.jdbc.driver", "/home/jovyan/work/mysql-connector-j-8.0.33.jar") \
    .save()
    return print('Data imported successfully')



def main_task(mysql_time, url, user, driver, password):

    print('-----------------------------Retrieving data from Cassandra-------------------------')
    df = spark.read.format("org.apache.spark.sql.cassandra").options(table="tracking",keyspace="realtime_data").load().where(col('ts')>= mysql_time)
    print('-----------------------------Selecting data from Cassandra-----------------------------')
    df = df.select('ts','job_id','custom_track','bid','campaign_id','group_id','publisher_id')
    df = df.filter(df.job_id.isNotNull())
    df.printSchema()

    print('-----------------------------Processing Cassandra Output-----------------------------')
    clicks_output = calculating_clicks(df)
    conversion_output = calculating_conversion(df)
    qualified_output = calculating_qualified(df)
    unqualified_output = calculating_unqualified(df)
    cassandra_output = process_final_data(clicks_output,conversion_output,qualified_output,unqualified_output)

    print('-----------------------------Merge Company Data-----------------------------')
    company = retrieve_company_data(url,driver,user,password)

    print('-----------------------------Finalizing Output-----------------------------')
    # Rename and select final columns
    final_output = cassandra_output.join(company,'job_id','left').drop(company.group_id).drop(company.campaign_id)
    final_output = final_output.select('job_id','date','hour','publisher_id','company_id','campaign_id','group_id','unqualified','qualified','conversions','clicks','bid_set','spend_hour')
    final_output = final_output.withColumnRenamed('date','dates').withColumnRenamed('hour','hours').withColumnRenamed('qualified','qualified_application').\
    withColumnRenamed('unqualified','disqualified_application').withColumnRenamed('conversions','conversion')

    # Add metadata columns
    final_output = final_output.withColumn('sources',lit('Cassandra'))
    final_output = final_output.withColumn('updated_at',date_format(current_timestamp(), 'yyyy-MM-dd HH:mm:ss'))
    final_output.printSchema()

    print('-----------------------------Import Output to MySQL-----------------------------')
    import_to_mysql(final_output)

    return print('-------------------------Task Finished---------------------------------')

    
    
if __name__ == '__main__':
    host = 'mysql'
    port = '3306'
    db_name = 'mydb'
    user = 'root'
    password = 'rootpass'
    url = 'jdbc:mysql://' + host + ':' + port + '/' + db_name
    driver = "com.mysql.cj.jdbc.Driver"

    print('The host is ' ,host)
    print('The port using is ',port)
    print('The db using is ',db_name)

    while True :
        start_time = datetime.datetime.now()

        cassandra_time = get_latest_time_cassandra()
        print('Cassandra latest time is {}'.format(cassandra_time))

        mysql_time = get_mysql_latest_time(url,driver,user,password)
        print('MySQL latest time is {}'.format(mysql_time))

        if cassandra_time > mysql_time : 
            main_task(mysql_time)
        else :
            print("No new data found")

        end_time = datetime.datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        print('Job takes {} seconds to execute'.format(execution_time))

        time.sleep(10)
    






 
