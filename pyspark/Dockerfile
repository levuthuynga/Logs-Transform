FROM jupyter/pyspark-notebook:latest

# Switch to the root user to gain write permissions for system directories
USER root

# Copy the Cassandra connector JAR file into Spark's jars directory
COPY spark-cassandra-connector-assembly_2.12-3.5.0.jar /usr/local/spark/jars/

# Copy the MySQL connector JAR file into Spark's jars directory
COPY mysql-connector-j-8.0.33.jar /usr/local/spark/jars/

# Set environment variables
ENV SPARK_HOME=/usr/local/spark
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PYSPARK_PYTHON=python3

# Install dependencies
RUN pip install pyspark mysql-connector-python cassandra-driver findspark time-uuid

# Switch back to the default user (`jovyan`) to run the notebook
USER ${NB_USER}

# Copy additional configuration files (if needed)
COPY spark-defaults.conf $SPARK_HOME/conf/

WORKDIR /home/jovyan/work

CMD ["start-notebook.sh"]
