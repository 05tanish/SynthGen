import json
from unittest.mock import MagicMock
from backend.app.agents.requirement_schema_agent import RequirementSchemaAgent
from backend.app.schemas.common import RequirementAnalysis, ColumnSchema, ColumnConstraint
from backend.app.tools.schema_validator import schema_validator
from backend.app.tools.schema_generator import schema_generator

agent = RequirementSchemaAgent()
dummy_response = RequirementAnalysis(
    dataset_name="customer_dataset",
    row_count=50000,
    columns=[
        ColumnSchema(
            name="age",
            semantic_type="integer",
            description="Age of customer",
            constraints=ColumnConstraint(min=18, max=60)
        )
    ],
    relationships=[],
    business_rules=[],
    assumptions=["Assumed missing values are none"]
)
agent.analyze_requirement = MagicMock(return_value=dummy_response)

print("Analyzing requirement...")
analysis = agent.analyze_requirement("Create a customer dataset with 50,000 rows. Age between 18 and 60.")

print("Validating schema...")
schema_validator(analysis)

print("Generating schema...")
schema = schema_generator(analysis)

print(json.dumps(schema, indent=2))
