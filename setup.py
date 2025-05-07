"""Setup script for m365proxy module."""
import os
import re

from setuptools import find_packages, setup

def read_init(field: str) -> str:
    """Read a field from the __init__.py file."""
    init_file = os.path.join("m365proxy", "__init__.py")
    pattern = rf'^__{field}__\s*=\s*[\'"]([^\'"]+)[\'"]'

    with open(init_file, "r", encoding="utf-8") as f:
        for line in f:
            match = re.match(pattern, line)
            if match:
                return match.group(1)

    raise RuntimeError(f"Unable to find __{field}__ in {init_file}.")


setup(
    name="m365proxy",
    version=read_init("version"),
    description=read_init("description"),
    long_description=open("README_PYPI.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author=read_init("author"),
    author_email=read_init("author_email"),
    url="https://github.com/sh0rch/m365proxy",
    packages=find_packages(include=["m365proxy", "m365proxy.*"]),
    include_package_data=True,
    license="MIT",
    keywords="m365 smtp pop3 smtps pop3s starttls proxy mail email graph",
    install_requires=[
        "httpx",
        "aiosmtpd",
        "python-dotenv",
        "colorlog",
        "bcrypt",
        "cryptography",
        "msal",
        "pysocks",
        "python-jose",
    ],
    entry_points={
        "console_scripts": [
            "m365-proxy=m365proxy.cli:main"
        ]
    },
    python_requires='>=3.9.7',
)
