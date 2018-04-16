from setuptools import setup, Extension

description="A simple validation framework"
long_description="""
Validino is a simple validation framework with a functional
syntax.
"""
platforms="OS Independent"

keywords=["validation", "forms"]
classifiers=[_f for _f in """
Development Status :: 4 - Beta
Intended Audience :: Developers
Operating System :: OS Independent
Programming Language :: Python
Topic :: Software Development :: Libraries :: Python Modules
""".split('\n') if _f]

__data__ = dict(
    author='Jacob Smullyan',
    author_email='jsmullyan@gmail.com',
    url='http://code.google.com/p/validino',
    description=description,
    long_description=long_description,
    keywords=keywords,
    platforms=platforms,
    license='MIT',
    name='validino',
    version='0.3',
    zip_safe=True,
    include_package_data=True,
    packages=['validino'],
    package_dir={'' : 'src'},
    test_suite='nose.collector')

if __name__ == '__main__':
    setup(**__data__)
