---
slug: setup
type: note
graph: gitnexus
---

#!/usr/bin/env python3
"""Quant HQ — Professional Trading Command Center.

Packaging for pip install. The core stack runs on Python stdlib only;
optional bridge dependencies are listed as extras.
"""

from setuptools import setup, find_packages

setup(
    name="quant-hq",
    version="1.0.0",
    description="Quant HQ — Professional Trading Command Center",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Quant HQ",
    python_requires=">=3.10",
    packages=find_packages(exclude=("tests", "tests.*", "backups", "agent-reports")),
    include_package_data=True,
    install_requires=[
        "PyYAML>=6.0",
    ],
    extras_require={
        "mt5": ["MetaTrader5>=5.0.40"],
        "telegram": ["telethon>=1.34.0"],
        "ocr": ["Pillow>=10.0.0"],
        "quant": ["numpy>=1.24.0"],
        "dev": ["pytest>=7.0.0"],
        "all": [
            "MetaTrader5>=5.0.40",
            "telethon>=1.34.0",
            "Pillow>=10.0.0",
            "numpy>=1.24.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "quant-hq=hq:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Win32 (MS Windows)",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
)

