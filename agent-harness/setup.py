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
    entry_points={
        "console_scripts": [
            "cli-anything-amazon-ads-ops-workbench=cli_anything.amazon_ads_ops_workbench.amazon_ads_ops_workbench_cli:cli",
        ]
    },
    python_requires=">=3.10",
)
