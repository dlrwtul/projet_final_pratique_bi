import dagster as dg

pipeline_complet = dg.define_asset_job(name="pipeline_complet", selection="*")

schedule_quotidien = dg.ScheduleDefinition(
    job=pipeline_complet,
    cron_schedule="0 2 * * *",
    execution_timezone="Africa/Dakar",
)