import unittest
import json
import log_analyzer
import os
import datetime
import time
import shutil
import hashlib


class LogAnalyzerTest(unittest.TestCase):
    def testUpdateConfig(self):
        salt = int(time.mktime(datetime.datetime.now().timetuple()))
        config = {'param1': 'value1',
                  'param2': 'value2',
                  'param3': 'value3',
                  'CONFIG_DEFAULT': '/tmp/some_config' + str(salt)}
        config_file = "/tmp/testconfigfile" + str(salt)
        config_file_data = {'param2': 'valueNew2',
                            'param4': 'valueNew4',
                            'param5': 'valueNew5'}
        result = {'CONFIG_DEFAULT': '/tmp/some_config' + str(salt),
                  'param1': 'value1',
                  'param2': 'valueNew2',
                  'param3': 'value3',
                  'param4': 'valueNew4',
                  'param5': 'valueNew5'}

        with open(config_file, 'w') as f:
            f.write(json.dumps(config_file_data))
        testresult = log_analyzer.update_config(config_file, config)
        self.assertEqual(result, testresult)

        config_file_data = {}
        with open(config_file, 'w') as f:
            f.write(json.dumps(config_file_data))
        testresult = log_analyzer.update_config(config_file, config)
        self.assertEqual(config, testresult)

        os.remove(config_file)
        testresult = log_analyzer.update_config(config_file, config)
        self.assertEqual(config, testresult)

    def testGetLastLog(self):
        salt = int(time.mktime(datetime.datetime.now().timetuple()))
        work_dir = '/tmp/some_work_dir' + str(salt)
        os.makedirs(work_dir)
        files = ['nginx-access-ui.log-20180601.txt',
                 'nginx-access-ui.log-20180304',
                 'nginx-access-ui.log-20180629.gz',
                 'nginx-access-ui.log-20180701',
                 'nginx-access-ui.log-20180702.bz2']
        for f in files:
            os.system("touch {}".format(os.path.join(work_dir, f)))

        log = log_analyzer.get_log_name(work_dir)

        self.assertEqual(os.path.join(work_dir, files[3]), log.log_name)
        self.assertEqual(log.log_date, '2018.07.01')

        os.remove(os.path.join(work_dir, files[3]))
        log = log_analyzer.get_log_name(work_dir)

        self.assertEqual(os.path.join(work_dir, files[2]), log.log_name)
        self.assertEqual(log.log_date, '2018.06.29')

        os.remove(os.path.join(work_dir, files[2]))
        log = log_analyzer.get_log_name(work_dir)

        self.assertEqual(os.path.join(work_dir, files[0]), log.log_name)
        self.assertEqual(log.log_date, '2018.06.01')

        shutil.rmtree(work_dir)

    def testPercentage(self):
        p = log_analyzer.percentage(41, 100)
        self.assertAlmostEqual(p, 41, places=2)

        p = log_analyzer.percentage(22.2, 100)
        self.assertAlmostEqual(p, 22.2, places=2)

    def testMedian(self):
        t = [1, 1, 2, 3]
        median = log_analyzer.median(t)
        self.assertAlmostEqual(median, 1.5, places=2)

        t = [1, 2, 3]
        median = log_analyzer.median(t)
        self.assertAlmostEqual(median, 2, places=2)

        t = [1.1, 2.2, 2.3, 3.8]
        median = log_analyzer.median(t)
        self.assertAlmostEqual(median, 2.25, places=2)


if __name__ == '__main__':
    unittest.main()
