from setuptools import setup, find_packages

setup(
    name="csgo",
    version="0.1",
    packages=find_packages(),
    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires=[
        "pandas>=0.25.3",
        "numpy>=1.18.1",
        "scipy>=1.4.1",
        "matplotlib>=3.1.2",
        "textdistance>=4.2.0",
    ],
    package_data={
        # If any package contains *.txt or *.rst files, include them:
        "": [
            "*.go",
            "data/map/*.png",
            "data/nav/*.nav",
            "data/nav/*.xz",
            "*.mod",
            "*.sum",
        ]
    },
    # metadata to display on PyPI
    author="Peter Xenopoulos",
    author_email="xenopoulos@nyu.edu",
    description="Counter-Strike: Global Offensive data parsing, analysis and visualization data structures and functions",
    keywords="esports sports-analytics csgo",
    url="https://github.com/pnxenopoulos/csgo",  # project home page, if any
    project_urls={
        "Issues": "https://github.com/pnxenopoulos/csgo/issues",
        "Documentation": "https://github.com/pnxenopoulos/csgo/",
        "Github": "https://github.com/pnxenopoulos/csgo/",
    },
    classifiers=["License :: OSI Approved :: Python Software Foundation License"],
)
