from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='easymdp3',
      version='0.1',
      description='Library for combining MDPs and solving them for cognitive '+
                  'science research',
      url='https://github.com/markkho/easymdp3',
      author="Mark Ho",
      author_email='mark.ho.cs@gmail.com',
      license='MIT',
      packages=['easymdp3'],
      install_requires=[
          'markdown',
      ],
      test_suite='nose.collector',
      tests_require=['nose'],
      zip_safe=False)