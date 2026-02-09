# Development Environment Configuration
# Optimized for cost savings and development workflows

environment = "dev"
aws_region  = "us-east-1"
owner       = "data-engineering"

# S3 Lifecycle - Aggressive cleanup for dev
bronze_glacier_transition_days = 90
silver_glacier_transition_days = 180
temp_expiration_days           = 3

# Glue - Minimal resources
glue_worker_type       = "G.1X"
glue_number_of_workers = 2

# Redshift - Minimal with aggressive auto-pause
redshift_base_capacity = 8
redshift_max_capacity  = 16

# Monitoring - Low threshold for cost awareness
budget_threshold = 50
alert_email      = ""  # Set your email here
