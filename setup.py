import setuptools
from setuptools.command.install import install as install_

class InstallCommand(install_):
    def run(self):
        import stanza
        import spacy
        stanza.download("en", resources_url="stanfordnlp", processors="tokenize,pos")
        spacy.cli.download("en_core_web_sm", exclude=["tagger", "attribute_ruler", "ner"])
        install_.run(self)

with open("./README.md", "r", encoding="utf-8") as f:
    long_description = f.read()
with open("./src/prev/about.py", "r", encoding="utf-8") as f:
    about = {}
    exec(f.read(), about)
setuptools.setup(
    name="prev",
    version=about["__version__"],
    author="Long Tan",
    author_email="tanloong@foxmail.com",
    url="https://github.com/tanloong/prepositional-verb-identifier",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    cmdclass={"install":InstallCommand},
    description="Prepositional Verb Identifier",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=['stanza', 'spacy>=3.5.1'],
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.6",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.6,<=3.9",
    entry_points={"console_scripts": ["prev = prev:main"]},
)
