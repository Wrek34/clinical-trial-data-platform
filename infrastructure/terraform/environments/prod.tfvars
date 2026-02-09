# Production Environment Configuration
# Optimized for reliability, performance, and regulatory compliance

environment = "prod"
aws_region  = "us-east-1"
owner       = "data-engineering"

# S3 Lifecycle - Regulatory retention requirements
bronze_glacier_transition_days = 365   # 1 year before Glacier
silver_glacier_transition_days = 730   # 2 years before Glacier
temp_expiration_days           = 7     # 1 week

# Glue - Production capacity
glue_worker_type       = "G.2X"
glue_number_of_workers = 10

# Redshift - Production capacity with room to scale
redshift_base_capacity = 32
redshift_max_capacity  = 128

# Monitoring - Production budget
budget_threshold = 500
alert_email      = ""  # Set production alerts email
