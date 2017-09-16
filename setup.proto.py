from setuptools import setup, find_packages

setup(
    name='hiku_proto',
    version='0.1.0',
    description='Protobufs for Hiku project',
    author='Vladimir Magamedov',
    author_email='vladimir@magamedov.com',
    url='https://github.com/vmagamedov/hiku',
    packages=find_packages(),
    namespace_packages=['hiku'],
    include_package_data=True,
    license='BSD',
    install_requires=['protobuf'],
    entry_points={
        'protobuf_proto': [
            'hiku=hiku_proto',
        ]
    },
)
