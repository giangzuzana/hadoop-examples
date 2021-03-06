import sys
import argparse
import subprocess

queue = 'staff'
__version__ = '2.5.0'
prefix = 'trozamon_testing'
input_unstructured = '/'.join([prefix, 'input_unstructured'])
input_structured = '/'.join([prefix, 'input_structured'])
output_prefix = '/'.join([prefix, 'output'])

big_description = """Hadoop and related software cluster tester. Given the
fast-paced nature of Hadoop, Spark, Hive, and other technologies, running a
test suite after an upgrade can ensure that all expected functionality
continues to work.  This script will generate and upload data to
$HOME/trozamon_testing in HDFS."""

def hdfs_mkdir(dir):
    if subprocess.call('hdfs dfs -test -d ' + dir, shell=True) != 0:
        if subprocess.call('hdfs dfs -mkdir ' + dir, shell=True) != 0:
            print('Failed to create ' + dir + ' in HDFS')
            return 1
    return 0

def hdfs_put(local, remote):
    if subprocess.call('hdfs dfs -test -f ' + remote, shell=True) != 0:
        if subprocess.call('hdfs dfs -put ' + local + ' ' + remote,
                shell=True) != 0:
            print('Failed to upload ' + local + ' to ' + remote)
            return 1
    return 0

def hdfs_rmdir(dir):
    if subprocess.call('hdfs dfs -test -d ' + dir, shell=True) == 0:
        return subprocess.call('hdfs dfs -rm -r ' + dir, shell=True)
    return 0

def test_hadoop_java():
    outdir = '/'.join([output_prefix, 'hadoop_java'])
    cmd = ' '.join([
        'yarn jar hadoop/target/hadoop-examples-hadoop-' + __version__ + '.jar',
        'com.alectenharmsel.research.LineCount',
        '-Dmapreduce.job.queuename=' + queue,
        input_unstructured,
        outdir
        ])

    if hdfs_rmdir(outdir) != 0:
        return 1

    print('Testing Hadoop Java by running:')
    print(cmd)

    return subprocess.call(cmd, shell=True)

def test_hadoop_streaming():
    outdir = '/'.join([output_prefix, 'hadoop_streaming'])
    cmd = ' '.join([
        'yarn jar /usr/lib/hadoop-mapreduce/hadoop-streaming.jar',
        '-Dmapreduce.job.queuename=' + queue,
        '-input ' + input_unstructured,
        '-output ' + outdir,
        '-mapper python/srctok-map.py -reducer python/sum.py',
        '-file python/srctok-map.py -file python/sum.py'
        ])

    if hdfs_rmdir(outdir) != 0:
        return 1

    print('Testing Hadoop Streaming by running:')
    print(cmd)

    return subprocess.call(cmd, shell=True)

def test_pig():
    cmd = ' '.join([
        'pig',
        '-Dmapreduce.job.queuename=' + queue,
        '-f pig/cluster_test.pig'
        ])

    print('Testing Pig by running:')
    print(cmd)

    return subprocess.call(cmd, shell=True)

def test_spark():
    outdir = '/'.join([output_prefix, 'spark'])
    cmd = ' '.join([
        'spark-submit',
        '--master yarn-client',
        '--queue ' + queue,
        '--class com.alectenharmsel.research.spark.LineCount',
        'spark/target/hadoop-examples-spark-' + __version__ + '.jar',
        input_unstructured,
        outdir
        ])

    if hdfs_rmdir(outdir) != 0:
        return 1

    print('Testing Spark by running:')
    print(cmd)

    return subprocess.call(cmd, shell=True)

def test_pyspark():
    cmd = ' '.join([
        'spark-submit',
        '--master yarn-client',
        '--queue ' + queue,
        'python/spark/lc.py',
        input_unstructured
        ])

    print('Testing PySpark by running:')
    print(cmd)

    return subprocess.call(cmd, shell=True)

def test_hive():
    cmd = ' '.join([
        'hive',
        '--hiveconf mapreduce.job.queuename=' + queue,
        '-f hive/cluster_test.sql'
        ])

    print('Testing Hive by running:')
    print(cmd)

    return subprocess.call(cmd, shell=True)

def run():
    parser = argparse.ArgumentParser(description=big_description)

    parser.add_argument('--all',
            action='store_true',
            help='Run all codes that would be run by using all possible flags')
    parser.add_argument('--hadoop-java',
            action='store_true',
            help='Run a selection of Java codes written for Hadoop')
    parser.add_argument('--hadoop-streaming',
            action='store_true',
            help='Run a selection of Python codes written for Hadoop')
    parser.add_argument('--pig',
            action='store_true',
            help='Run a selection of Pig scripts')
    parser.add_argument('--spark',
            action='store_true',
            help='Run a selection of Scala codes written for Spark')
    parser.add_argument('--pyspark',
            action='store_true',
            help='Run a selection of Python codes written for Spark')
    parser.add_argument('--hive',
            action='store_true',
            help='Run a selection of Hive queries')

    parsed_args = parser.parse_args()

    tests = list()
    if parsed_args.all:
        parsed_args.hadoop_java = True
        parsed_args.hadoop_streaming = True
        parsed_args.pig = True
        parsed_args.hive = True
        parsed_args.spark = True
        parsed_args.pyspark = True

    if parsed_args.hadoop_java:
        tests.append(test_hadoop_java)
    if parsed_args.hadoop_streaming:
        tests.append(test_hadoop_streaming)
    if parsed_args.pig:
        tests.append(test_pig)
    if parsed_args.pyspark:
        tests.append(test_pyspark)
    if parsed_args.spark:
        tests.append(test_spark)
    # Hive should always be last - it munges data
    if parsed_args.hive:
        tests.append(test_hive)

    print('Running "mvn package -DskipTests"...')
    if subprocess.call('mvn package -DskipTests', shell=True) != 0:
        print('Maven build failed. Are you running this in the root ' +
                'directory of the repo?')
        return 1

    print('Creating directory structure...')
    err = hdfs_mkdir(prefix)
    if err != 0:
        return err
    err = hdfs_mkdir(input_unstructured)
    if err != 0:
        return err
    err = hdfs_mkdir(input_structured)
    if err != 0:
        return err
    err = hdfs_mkdir(output_prefix)
    if err != 0:
        return err
    print('Uploading unstructured data...')
    err = hdfs_put('pom.xml', '/'.join([input_unstructured, 'pom.xml']))
    if err != 0:
        return err
    print('Uploading structured data...')
    err = hdfs_put('structured.data', '/'.join([input_structured, 'data']))
    if err != 0:
        return err

    print('Starting to run tests...')
    results = {}
    ret = 0
    for test in tests:
        res = test()
        if res == 0:
            results[test.__name__] = True
        else:
            ret = 1
            results[test.__name__] = False

    for test in sorted(results.keys()):
        if results[test]:
            print(test + ': SUCCESS')
        else:
            print(test + ': FAILURE')

    return ret

if __name__ == '__main__':
    sys.exit(run())
