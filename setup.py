from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="zoho-vertical-sdk",
    version="1.0.0",
    author="Your Name",
    author_email="you@example.com",
    description="Python SDK for Zoho Vertical Studio REST APIs v6",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourname/zoho-vertical-sdk",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-mock>=3.0",
            "responses>=0.23",
            "black",
            "ruff",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="zoho vertical-studio crm sdk api",
)
