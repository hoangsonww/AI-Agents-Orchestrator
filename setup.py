"""
Setup script for AI Coding Tools Collaborative
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="ai-orchestrator",
    version="1.0.0",
    description="Orchestration system for collaborative AI coding assistants",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AI Orchestrator Team",
    python_requires=">=3.8",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.0",
        "pyyaml>=6.0",
        "colorama>=0.4.6",
        "rich>=13.0.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "ai-orchestrator=ai-orchestrator:cli",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
