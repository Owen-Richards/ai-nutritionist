# Test Fixtures System

This directory contains a comprehensive test fixture system for the AI Nutritionist application. The fixtures provide standardized, reusable test data and mock services to ensure consistent and reliable testing.

## Structure

```
tests/fixtures/
├── __init__.py              # Exports all fixtures
├── user_fixtures.py         # User profiles and accounts
├── nutrition_fixtures.py    # Meal plans, recipes, nutrition data
├── health_fixtures.py       # Health metrics, exercise, wearables
├── payment_fixtures.py      # Subscriptions, payments, billing
└── mock_services.py         # External service mocks
```

## User Fixtures

### Basic Fixtures

- `create_test_user()` - Basic free tier user
- `create_premium_user()` - Premium subscription user
- `create_family_account()` - Family account with multiple members

### Factory Pattern

```python
def test_user_creation(user_factory):
    # Create specialized users
    weight_loss_user = user_factory.weight_loss_user()
    diabetic_user = user_factory.diabetic_user()
    family_user = user_factory.family_user(family_size=5)
```

### Builder Pattern

```python
def test_custom_user(user_profile_builder):
    user = (user_profile_builder
            .with_phone("+1555123456")
            .with_subscription(SubscriptionTier.PREMIUM)
            .with_dietary_restrictions([DietaryRestriction.VEGETARIAN])
            .with_wearable("fitbit", "device_123")
            .build())
```

## Nutrition Fixtures

### Meal Plans

- `create_meal_plan()` - Standard weekly meal plan
- `meal_plan_factory.vegetarian_plan()` - Vegetarian meal plan
- `meal_plan_factory.weight_loss_plan()` - Weight loss focused plan
- `meal_plan_factory.family_plan()` - Family-sized portions

### Recipes and Ingredients

```python
def test_recipes(recipe_factory, ingredient_factory):
    # Create specific meal recipes
    breakfast = recipe_factory.breakfast_recipe()
    dinner = recipe_factory.dinner_recipe()

    # Create custom ingredients
    protein = ingredient_factory.protein_source("Salmon")
    vegetable = ingredient_factory.vegetable("Spinach")
```

### Nutrition Goals

```python
def test_nutrition_goals(nutrition_goals_collection):
    weight_loss_goals = nutrition_goals_collection['weight_loss']
    muscle_gain_goals = nutrition_goals_collection['muscle_gain']
    diabetic_goals = nutrition_goals_collection['diabetic']
```

## Health Data Fixtures

### Health Metrics

- `create_health_metrics()` - Basic health metrics
- `weight_loss_journey` - Weight loss progression over time
- `diabetic_monitoring_data` - Blood glucose tracking

### Exercise Data

```python
def test_exercise_tracking(exercise_factory):
    # Create workout data
    strength_workout = exercise_factory.create_workout(
        workout_type="strength_training"
    )

    # Generate weekly summary
    weekly_summary = exercise_factory.weekly_activity_summary()

    # Create steps history
    steps_data = exercise_factory.daily_steps_data(days=30)
```

### Wearable Integration

```python
def test_wearables(wearable_factory):
    fitbit = wearable_factory.create_fitbit_integration()
    apple_watch = wearable_factory.create_apple_watch_integration()
    sync_data = wearable_factory.create_sync_data("fitbit")
```

## Payment Fixtures

### Subscriptions

```python
def test_subscriptions(subscription_factory):
    # Different subscription states
    active_sub = subscription_factory.active_premium()
    trial_sub = subscription_factory.trialing_subscription()
    canceled_sub = subscription_factory.canceled_subscription()
    family_sub = subscription_factory.family_subscription()
```

### Payment Methods

```python
def test_payments(payment_method_factory):
    visa_card = payment_method_factory.create_credit_card(
        last_four="4242", brand="visa"
    )
    paypal = payment_method_factory.create_paypal()
```

### Billing History

```python
def test_billing(invoice_factory, billing_history):
    paid_invoice = invoice_factory.paid_invoice()
    failed_invoice = invoice_factory.failed_invoice()

    # Use complete billing history
    assert len(billing_history) == 6  # 6 months of invoices
```

## Mock Services

### External API Mocks

All external services are mocked to ensure tests run independently:

```python
def test_external_services(mock_twilio, mock_stripe, mock_edamam):
    # Test SMS sending
    result = mock_twilio.send_sms("+1234567890", "Test message")
    assert result['success'] is True

    # Test payment processing
    customer = mock_stripe.create_customer("test@example.com")
    subscription = mock_stripe.create_subscription(
        customer['id'], "price_premium_monthly"
    )

    # Test recipe search
    recipes = mock_edamam.search_recipes("chicken", max_results=5)
    assert len(recipes['hits']) <= 5
```

### AWS Service Mocks

```python
def test_aws_services(mock_dynamodb, mock_s3, mock_ses):
    # Test DynamoDB operations
    mock_dynamodb.put_item(
        TableName='users',
        Item={'user_id': 'test-user', 'data': 'test'}
    )

    # Test S3 operations
    mock_s3.put_object(
        Bucket='meal-plans',
        Key='plan-123.json',
        Body='{"plan": "data"}'
    )

    # Test email sending
    mock_ses.send_email(
        Source='noreply@app.com',
        Destination={'ToAddresses': ['user@example.com']},
        Message={'Subject': {'Data': 'Test'}, 'Body': {'Text': {'Data': 'Test'}}}
    )
```

## Complete Workflow Testing

### Isolated Environment

```python
def test_complete_workflow(isolated_test_environment):
    """Test with all external dependencies mocked"""
    env = isolated_test_environment

    # All services are isolated and mocked
    twilio = env['twilio']
    stripe = env['stripe']
    aws = env['aws']
    edamam = env['edamam']
```

### End-to-End Scenarios

```python
def test_user_journey(user_factory, meal_plan_factory, subscription_factory, mock_twilio):
    # Create user
    user = user_factory.premium_user()

    # Create subscription
    subscription = subscription_factory.active_premium(user.user_id)

    # Generate meal plan
    meal_plan = meal_plan_factory.create(user_id=user.user_id)

    # Send notification
    notification = mock_twilio.send_sms(
        user.phone_number,
        f"Your meal plan '{meal_plan.name}' is ready!"
    )

    # Verify complete workflow
    assert notification['success'] is True
```

## Error Scenario Testing

### Service Failures

```python
def test_service_failures(mock_twilio, mock_stripe):
    # Test SMS failures
    mock_twilio.set_failure_rate(0.1)  # 10% failure rate

    # Test payment failures
    mock_stripe.should_fail_payments = True
    result = mock_stripe.create_subscription("cus_123", "price_123")
    assert 'error' in result
```

### Rate Limiting

```python
def test_rate_limiting(mock_edamam):
    mock_edamam.rate_limited = True
    result = mock_edamam.search_recipes("chicken")
    assert result['status_code'] == 429
```

## Best Practices

### 1. Use Appropriate Fixtures

- Use factory methods for creating variations
- Use builder pattern for complex customization
- Use basic fixtures for simple test cases

### 2. Isolate External Dependencies

```python
def test_with_mocks(mock_twilio, mock_stripe):
    # All external calls are mocked
    # Tests run fast and independently
    pass
```

### 3. Test Data Consistency

```python
def test_data_relationships(user_factory, subscription_factory):
    user = user_factory.premium_user()
    subscription = subscription_factory.active_premium(user.user_id)

    # Ensure data relationships are maintained
    assert subscription.user_id == user.user_id
```

### 4. Error Scenarios

```python
def test_error_handling(mock_stripe):
    mock_stripe.should_fail_payments = True
    # Test how your code handles payment failures
```

## Usage Examples

### Simple Test

```python
def test_basic_user_creation(create_test_user):
    user = create_test_user
    assert user.subscription_tier == SubscriptionTier.FREE
```

### Complex Integration Test

```python
def test_meal_plan_generation(
    user_factory,
    meal_plan_factory,
    mock_edamam,
    mock_dynamodb
):
    # Create user with dietary restrictions
    user = (user_factory.base_user()
            .with_dietary_restrictions([DietaryRestriction.VEGETARIAN]))

    # Mock recipe search
    mock_edamam.search_recipes.return_value = {
        'hits': [{'recipe': {'label': 'Veggie Bowl'}}]
    }

    # Create meal plan
    meal_plan = meal_plan_factory.vegetarian_plan(user.user_id)

    # Verify vegetarian constraints
    assert "vegetarian" in meal_plan.dietary_restrictions
```

## Extending the Fixtures

### Adding New Fixtures

1. Create factory classes in appropriate fixture files
2. Add pytest fixtures at the bottom of the file
3. Export in `__init__.py`
4. Document usage examples

### Custom Factories

```python
class CustomFactory:
    @staticmethod
    def create_special_case(param1, param2):
        # Your custom logic here
        return special_object
```

The fixture system is designed to be comprehensive, maintainable, and easy to extend. It provides everything needed to test the AI Nutritionist application thoroughly while keeping tests fast and reliable.
