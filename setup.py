from setuptools import find_packages, setup

setup(
    name="patch1",
    version="1.0.0.dev1",
    description="Tame your Synth1 patches",
    url="https://github.com/thomashuss/patch1",
    author="thomashuss",
    license="MIT",
    packages=find_packages(include=['src']),
    install_requires=[
        'pandas>=1.2.3',
        'sklearn>=0.0',
        'tables>=3.6.1'
    ],
    include_package_data=True,
    entry_points={
        'gui_scripts': ['patch1=src.__init__:main']
    }
)
