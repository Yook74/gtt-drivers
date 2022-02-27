from setuptools import setup
import gtt

with open('README.md', 'r') as handle:
    long_description = handle.read()

setup(
    name='gtt_drivers',
    version=gtt.__version__,
    description='A driver package for the Matrix Orbital\'s GTT series of displays',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Yook74',
    author_email='andrewBlomen@gmail.com',
    url='https://github.com/Yook74/gtt-drivers',
    packages=['gtt'],
    install_requires=['pyserial']
)
