"""Setup script for the freelance lead scraper."""

from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="freelance-lead-scraper",
    version="0.1.0",
    description="FastMCP-based lead generation system for freelance platforms",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.8",
)
