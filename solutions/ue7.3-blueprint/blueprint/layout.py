# AWS Glue Blueprint — layout generator (Ü7.3).
#
# A blueprint is a parametrized TEMPLATE, not a finished workflow. generate_layout
# builds the workflow entities from the run-time parameters (declared in
# blueprint.cfg -> parameterSpec). Here: the single-job chain of Ü7.1,
# Trigger -> Crawler(raw) -> Job(orders-s3-to-parquet), parametrized so ONE
# template can produce MANY workflows (vary WorkflowName / SourcePath).
#
# Order is NOT expressed as a list: the Job's DependsOn={crawler: "SUCCEEDED"}
# makes the blueprint run generate the CONDITIONAL trigger, plus a start trigger
# for the crawler, automatically.
#
# Two kinds of parameters flow in via user_params: STRUCTURAL ones (WorkflowName,
# SourcePath, RoleArn) shape the entities themselves; TargetFormat is a RUN-TIME
# value — set here as the workflow's DefaultRunProperties["target_format"], the
# same property the job reads at run time with get_workflow_run_properties
# (deck 7.5). The blueprint is the API way to seed that default run property.

from awsglue.blueprint.workflow import Workflow, Entities
from awsglue.blueprint.job import Job
from awsglue.blueprint.crawler import Crawler


def generate_layout(user_params, system_params):
    role = user_params["RoleArn"]

    raw_crawler = Crawler(
        Name="raw",
        Role=role,
        DatabaseName="raw",
        Targets={"S3Targets": [{"Path": user_params["SourcePath"]}]},
    )

    transform_job = Job(
        Name="orders-s3-to-parquet",
        Role=role,
        Command={
            "Name": "glueetl",
            "ScriptLocation": user_params["ScriptLocation"],
            "PythonVersion": "3",
        },
        DefaultArguments={"--TARGET_PATH": user_params["TargetPath"]},
        GlueVersion="4.0",
        DependsOn={raw_crawler: "SUCCEEDED"},
    )

    return Workflow(
        Name=user_params["WorkflowName"],
        # Seed the default run property the job reads at run time (deck 7.5).
        DefaultRunProperties={"target_format": user_params["TargetFormat"]},
        Entities=Entities(Crawlers=[raw_crawler], Jobs=[transform_job]),
    )
