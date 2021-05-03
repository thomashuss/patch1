from setuptools import find_packages, setup

setup(
    name="patch1",
    version="1.0.0.dev1",
    description="Tame your Synth1 patches",
    url="https://github.com/intrlocutr/patch1",
    author="intrlocutr",
    author_email="intrlocutr@outlook.com",
    license="MIT",
    packages=find_packages(include=['src']),
    install_requires=[
        'pandas>=1.2.3',
        'sklearn>=0.0',
        'tables>=3.6.1',
        'tkinterdnd2>=0.3.0'
    ],
    include_package_data=True,
    entry_points={
        'console_scripts': ['patch1=src.__init__:main']
    }
)