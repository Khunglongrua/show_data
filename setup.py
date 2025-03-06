from setuptools import setup, find_packages

setup(
    name='show_data',
    version='0.1',
    packages=find_packages(),
    py_modules=['ichimoku_plot'],
    install_requires=[
        'ccxt',
        'ta',
        'mplfinance',
        'pandas',
        'numpy',
        'matplotlib'
    ],
    description='Package for plotting Ichimoku Cloud',
    author='Khunglongrua',
    url='https://github.com/Khunglongrua/show_data',
)
