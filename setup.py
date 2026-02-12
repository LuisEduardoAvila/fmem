"""
Setup script for fmem - FAISS Memory Search Skill
"""

from setuptools import setup, find_packages

setup(
    name='fmem-skill',
    version='1.0.0',
    description='FAISS-based memory search skill with semantic vector search',
    long_description='Semantic memory search using FAISS embeddings, optimized for low-resource systems with zero cloud dependencies.',
    author='SmartSpud (Bob)',
    author_email='luis@example.com',
    url='https://github.com/LuisEduardoAvila/DarthSpudFmem',
    license='MIT',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    keywords='memory search semantic FAISS embeddings offline',
    python_requires='>=3.8',
    install_requires=[
        'faiss-cpu>=1.7.0',
        'nomic-embed>=1.0.0',
    ],
    entry_points={
        'console_scripts': [
            'fmem=fmem:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
    project_urls={
        'Bug Reports': 'https://github.com/LuisEduardoAvila/DarthSpudFmem/issues',
        'Source': 'https://github.com/LuisEduardoAvila/DarthSpudFmem',
    },
)