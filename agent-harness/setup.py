from setuptools import find_namespace_packages, setup


setup(
    name="cli-anything-amazon-ads-ops-workbench",
    version="0.1.0",
    description="CLI-Anything harness for the Amazon Ads Ops Workbench",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    include_package_data=True,
    package_data={
        "cli_anything.amazon_ads_ops_workbench": ["skills/*.md"],
    },
    install_requires=[
        "click>=8.1.7",
        "prompt_toolkit>=3.0.0",
    ],
    extras_require={
        'server': ['fastapi>=0.115,<1', 'uvicorn>=0.30,<1', 'sqlalchemy>=2,<3',
                   'psycopg[binary]>=3.2,<4', 'mcp>=1.20,<2', 'cryptography>=44',
                   'paramiko>=3.4,<6'],
    },
    entry_points={
        "console_scripts": [
            "cli-anything-amazon-ads-ops-workbench=cli_anything.amazon_ads_ops_workbench.amazon_ads_ops_workbench_cli:cli",
            "ads-control=cli_anything.amazon_ads_ops_workbench.control_plane.manage:main",
        ]
    },
    python_requires=">=3.10",
)
