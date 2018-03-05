import luigi, time

# superclass that defines withConfig() method
class ConfigurableTask(luigi.Task):

    def withConfig(self, config):
        self.build_config = config
        return self

# Individual tasks inherit from ConfigurableTask
class MyTask(ConfigurableTask):
    p1 = luigi.parameter.Parameter()

    def output(self):
        return {"output": luigi.LocalTarget("/home/user/foo.txt")}

    def run(self):
        print "Task running..."
        time.sleep(10)
        # make sure we can still access config from superclass
        print "Config:  " + str(self.config)