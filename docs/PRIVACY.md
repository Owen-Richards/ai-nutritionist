# 🔒 Privacy & Data Protection

## Overview

The AI Nutritionist Assistant is designed with privacy-first principles, ensuring GDPR compliance, user data sovereignty, and transparent consent management. Our approach prioritizes user trust while enabling personalized nutrition coaching.

## 🛡️ Privacy Principles

### 1. Data Minimization
- **Collect Only What's Needed**: Start with allergies + primary goal only
- **Progressive Collection**: Gather additional data based on user engagement
- **Purpose Limitation**: Use data solely for nutrition coaching and service improvement
- **Retention Limits**: Automatically delete inactive user data after 2 years

### 2. User Control
- **Granular Consent**: Users control what data is collected and how it's used
- **Easy Deletion**: Complete data removal with simple "DELETE" command
- **Data Portability**: Export all user data in machine-readable format
- **Opt-Out Anytime**: Withdraw consent and stop data processing instantly

### 3. Transparency
- **Clear Explanations**: Plain language privacy notices
- **Data Usage Visibility**: Users can see exactly what data we have
- **Processing Transparency**: Explain how AI makes recommendations
- **Regular Updates**: Notify users of any privacy policy changes

## 📋 Data Categories & Legal Basis

### Personal Data Collected

#### Core Identity Data
```python
@dataclass
class CoreIdentityData:
    user_id: str                    # Hashed phone number
    phone_number_hash: str          # Irreversibly hashed for identification
    region_code: str               # For localization only
    created_at: datetime           # Account creation timestamp
    
    # Legal basis: Legitimate interest (service provision)
    # Retention: Duration of account + 30 days
```

#### Health & Preference Data  
```python
@dataclass
class HealthPreferenceData:
    allergies: List[str]           # Food allergies and intolerances
    dietary_restrictions: List[str] # Vegetarian, vegan, kosher, etc.
    health_goals: List[str]        # Weight management, energy, etc.
    medical_conditions: List[str]   # Only if user volunteers information
    
    # Legal basis: Explicit consent
    # Retention: Until consent withdrawal
    # Special category: Health data (Article 9 GDPR)
```

#### Behavioral Data
```python
@dataclass
class BehavioralData:
    meal_preferences: Dict         # Learned from interactions
    conversation_patterns: Dict    # Engagement analytics
    usage_frequency: Dict         # Feature usage patterns
    satisfaction_scores: List[int] # Meal plan ratings
    
    # Legal basis: Legitimate interest (service improvement)
    # Retention: 18 months or account deletion
```

#### Visual Data (Photos)
```python
@dataclass
class VisualData:
    meal_photos: List[str]         # S3 URLs (temporary)
    photo_analysis: Dict          # Nutrition extraction results
    user_corrections: List[str]    # Manual photo corrections
    
    # Legal basis: Explicit consent
    # Retention: 30 days (photos), 2 years (analysis)
    # Processing: Local analysis, no third-party sharing
```

## 🤝 Consent Management

### Progressive Consent Flow

#### Initial Onboarding (Minimal Consent)
```python
class InitialConsent:
    def collect_minimal_consent(self, phone_number):
        consent_request = {
            'message': """
            Welcome to AI Nutritionist! 🥗
            
            To get started, I need your consent to:
            ✅ Store your food allergies and preferences
            ✅ Send you personalized meal plans via WhatsApp
            ✅ Learn from your feedback to improve suggestions
            
            Reply YES to continue, or STOP to opt out.
            
            Full privacy policy: [link]
            """,
            'required_consents': [
                'basic_data_processing',
                'whatsapp_communication',
                'preference_learning'
            ],
            'legal_basis': 'explicit_consent'
        }
        
        return consent_request
    
    def record_consent(self, user_id, consent_response):
        if consent_response.upper() == 'YES':
            consent_record = ConsentRecord(
                user_id=user_id,
                timestamp=datetime.utcnow(),
                consent_type='initial_onboarding',
                consents_given=['basic_processing', 'communication'],
                ip_address=get_user_ip(user_id),
                user_agent=get_user_agent(user_id),
                consent_method='whatsapp_message'
            )
            
            store_consent_record(consent_record)
            return True
        
        return False
```

#### Feature-Specific Consent
```python
class FeatureConsent:
    def request_photo_consent(self, user_id):
        return {
            'message': """
            📸 Photo Meal Logging Available!
            
            I can analyze photos of your meals for instant nutrition feedback.
            
            To enable this feature, I need consent to:
            ✅ Process photos of your food
            ✅ Store nutrition analysis (photos deleted after 30 days)
            ✅ Use analysis to improve your meal plans
            
            Photos are processed privately and never shared.
            
            Enable photo logging? YES/NO
            """,
            'consent_type': 'photo_processing',
            'data_categories': ['visual_data', 'nutrition_analysis'],
            'retention_period': '30_days_photos_2_years_analysis'
        }
    
    def request_calendar_consent(self, user_id):
        return {
            'message': """
            🗓️ Calendar Integration Available!
            
            I can add your meal plans to Google Calendar with:
            ✅ Meal prep reminders
            ✅ Grocery shopping schedules  
            ✅ Cooking time blocks
            
            This requires access to read/write your calendar.
            
            Connect calendar? YES/NO
            """,
            'consent_type': 'calendar_integration',
            'third_party': 'google_calendar',
            'permissions': ['read_calendar', 'write_events']
        }
```

#### Household Consent Flow
```python
class HouseholdConsent:
    def initiate_household_linking(self, inviter_id, invitee_phone):
        # Double opt-in process for GDPR compliance
        
        # Step 1: Inviter consent
        inviter_consent = {
            'message': f"""
            👨‍👩‍👧‍👦 Household Meal Planning
            
            You're inviting {mask_phone_number(invitee_phone)} to link accounts.
            
            This will allow:
            ✅ Shared meal planning for your household
            ✅ Combined grocery lists
            ✅ Family nutrition tracking
            
            Their data remains private unless they explicitly share.
            
            Send invitation? YES/NO
            """,
            'consent_type': 'household_invitation',
            'data_sharing': 'meal_plans_only'
        }
        
        return inviter_consent
    
    def send_household_invitation(self, inviter_id, invitee_phone):
        verification_code = generate_secure_code()
        
        invitation = {
            'message': f"""
            🥗 AI Nutritionist Household Invitation
            
            {get_user_name(inviter_id)} invited you to join their meal planning!
            
            Benefits:
            ✅ Shared family meal plans
            ✅ Combined grocery savings
            ✅ Your data stays private (you control what's shared)
            
            Verification code: {verification_code}
            
            To join, reply: JOIN {verification_code}
            To decline: DECLINE
            
            Privacy policy: [link]
            """,
            'expiry': datetime.utcnow() + timedelta(hours=72),
            'consent_required': True
        }
        
        store_pending_invitation(inviter_id, invitee_phone, verification_code)
        send_sms(invitee_phone, invitation['message'])
    
    def process_household_consent(self, invitee_phone, response):
        if response.startswith('JOIN'):
            verification_code = response.split()[1]
            
            if verify_invitation_code(invitee_phone, verification_code):
                # Explicit consent for household data sharing
                consent_details = {
                    'data_shared': ['meal_preferences', 'allergies', 'meal_plans'],
                    'data_not_shared': ['conversation_history', 'photos', 'health_goals'],
                    'revocable': True,
                    'granular_control': True
                }
                
                record_household_consent(invitee_phone, consent_details)
                complete_household_linking(invitee_phone)
                
                return True
        
        return False
```

## 🗂️ Data Storage & Security

### Encryption Standards
```python
class DataSecurity:
    def encrypt_sensitive_data(self, data, data_category):
        encryption_keys = {
            'health_data': get_health_data_key(),      # Separate key for health data
            'preferences': get_preference_key(),        # User preference data
            'conversations': get_conversation_key(),    # Chat history
            'photos': get_photo_encryption_key()        # Visual data
        }
        
        key = encryption_keys[data_category]
        
        # AES-256-GCM encryption
        encrypted_data = encrypt_aes_gcm(data, key)
        
        return {
            'encrypted_data': encrypted_data,
            'encryption_method': 'AES-256-GCM',
            'key_id': key.id,
            'encrypted_at': datetime.utcnow()
        }
    
    def implement_data_isolation(self):
        # Separate databases for different data types
        databases = {
            'user_profiles': 'dynamodb_encrypted_user_data',
            'health_data': 'dynamodb_health_data_encrypted',  # Extra protection
            'conversation_logs': 'dynamodb_conversations',
            'analytics': 'dynamodb_anonymized_analytics'
        }
        
        # Network isolation
        vpc_configuration = {
            'private_subnets': True,
            'nat_gateway': True,
            'no_internet_gateway': True,  # No direct internet access
            'vpc_endpoints': ['dynamodb', 's3', 'bedrock']
        }
        
        return databases, vpc_configuration
```

### Data Anonymization
```python
class DataAnonymization:
    def anonymize_for_analytics(self, user_data):
        # Create anonymous analytics dataset
        anonymized = {
            'user_hash': hash_user_id(user_data.user_id),
            'region': generalize_location(user_data.region),
            'age_range': generalize_age(user_data.age),
            'dietary_pattern': generalize_diet(user_data.preferences),
            'engagement_level': calculate_engagement(user_data.usage),
            'satisfaction_trend': aggregate_satisfaction(user_data.ratings)
        }
        
        # Remove all personally identifiable information
        anonymized = remove_pii(anonymized)
        
        # Apply k-anonymity (k=5 minimum)
        anonymized = ensure_k_anonymity(anonymized, k=5)
        
        return anonymized
    
    def pseudonymize_for_ml(self, dataset):
        # Create training dataset with pseudonymized identifiers
        pseudonymized = {}
        
        for user_id, user_data in dataset.items():
            pseudo_id = generate_consistent_pseudonym(user_id)
            
            pseudonymized[pseudo_id] = {
                'meal_patterns': user_data.meal_patterns,
                'preference_evolution': user_data.preference_changes,
                'satisfaction_patterns': user_data.satisfaction_trends,
                'anonymized_demographics': generalize_demographics(user_data)
            }
        
        return pseudonymized
```

## 🔄 Data Subject Rights (GDPR Articles 15-22)

### Right of Access (Article 15)
```python
class DataAccess:
    def export_user_data(self, user_id):
        # Complete data export in machine-readable format
        user_data_export = {
            'personal_information': {
                'user_id': user_id,
                'phone_number': get_masked_phone(user_id),
                'account_created': get_creation_date(user_id),
                'last_activity': get_last_activity(user_id)
            },
            'preferences_and_goals': get_user_preferences(user_id),
            'meal_history': get_meal_logs(user_id),
            'conversation_history': get_conversations(user_id),
            'usage_analytics': get_usage_data(user_id),
            'consent_records': get_consent_history(user_id),
            'data_sharing': get_sharing_permissions(user_id)
        }
        
        # Generate downloadable package
        export_package = create_data_package(user_data_export)
        
        send_message(user_id, f"""
        📦 Your data export is ready!
        
        Download link: {export_package.url}
        (Link expires in 7 days)
        
        This package contains all data we have about you in JSON format.
        """)
        
        return export_package
```

### Right to Erasure (Article 17)
```python
class DataErasure:
    def delete_user_data(self, user_id, deletion_type='complete'):
        deletion_log = DataDeletionLog(
            user_id=user_id,
            deletion_requested=datetime.utcnow(),
            deletion_type=deletion_type,
            requester='user_self_service'
        )
        
        if deletion_type == 'complete':
            # Full account deletion
            self.delete_profile_data(user_id)
            self.delete_conversation_history(user_id)
            self.delete_meal_logs(user_id)
            self.delete_photos(user_id)
            self.anonymize_analytics_data(user_id)
            self.revoke_all_consents(user_id)
            
        elif deletion_type == 'specific_data':
            # Selective deletion (user choice)
            self.delete_conversation_history(user_id)
            # Keep anonymized meal patterns for service improvement
            
        # 30-day grace period for accidental deletions
        schedule_permanent_deletion(user_id, days=30)
        
        confirmation_message = f"""
        ✅ Data deletion initiated
        
        Your data will be permanently deleted in 30 days.
        
        To recover your account before then, reply RECOVER.
        
        Deletion reference: {deletion_log.reference_id}
        """
        
        send_final_message(user_id, confirmation_message)
        
        return deletion_log
```

### Right to Rectification (Article 16)
```python
class DataRectification:
    def correct_user_data(self, user_id, correction_request):
        # Allow users to correct their information
        corrections_applied = []
        
        if 'allergies' in correction_request:
            old_allergies = get_user_allergies(user_id)
            new_allergies = correction_request['allergies']
            
            update_user_allergies(user_id, new_allergies)
            corrections_applied.append(f"Allergies: {old_allergies} → {new_allergies}")
        
        if 'preferences' in correction_request:
            update_preferences(user_id, correction_request['preferences'])
            corrections_applied.append("Meal preferences updated")
        
        # Log correction for audit trail
        correction_log = DataCorrectionLog(
            user_id=user_id,
            corrections=corrections_applied,
            corrected_at=datetime.utcnow(),
            corrected_by='user_self_service'
        )
        
        store_correction_log(correction_log)
        
        return f"✅ Corrected: {', '.join(corrections_applied)}"
```

### Right to Data Portability (Article 20)
```python
class DataPortability:
    def generate_portable_export(self, user_id):
        # Structured data export for migration to other services
        portable_data = {
            'user_profile': {
                'format': 'json',
                'schema_version': '1.0',
                'exported_at': datetime.utcnow().isoformat(),
                'data': get_structured_profile(user_id)
            },
            'meal_preferences': {
                'format': 'json',
                'cuisines': get_cuisine_preferences(user_id),
                'allergies': get_allergies(user_id),
                'dietary_restrictions': get_dietary_restrictions(user_id)
            },
            'meal_history': {
                'format': 'csv',
                'schema': 'date,meal_type,description,calories,rating',
                'data': export_meal_history_csv(user_id)
            },
            'analytics': {
                'format': 'json',
                'usage_patterns': get_usage_analytics(user_id),
                'satisfaction_trends': get_satisfaction_data(user_id)
            }
        }
        
        return create_portable_package(portable_data)
```

## 📊 Privacy Compliance Monitoring

### Consent Tracking
```python
class ConsentCompliance:
    def audit_consent_status(self, user_id):
        consent_audit = {
            'user_id': user_id,
            'audit_date': datetime.utcnow(),
            'active_consents': get_active_consents(user_id),
            'withdrawn_consents': get_withdrawn_consents(user_id),
            'consent_renewal_due': check_consent_renewal(user_id),
            'data_processing_status': verify_processing_legality(user_id)
        }
        
        # Flag any compliance issues
        compliance_issues = []
        
        if consent_audit['consent_renewal_due']:
            compliance_issues.append('consent_renewal_required')
        
        if not consent_audit['active_consents']:
            compliance_issues.append('no_valid_consent_basis')
        
        consent_audit['compliance_status'] = 'compliant' if not compliance_issues else 'action_required'
        consent_audit['issues'] = compliance_issues
        
        return consent_audit
    
    def automated_compliance_check(self):
        # Daily compliance monitoring
        all_users = get_all_active_users()
        
        for user_id in all_users:
            audit_result = self.audit_consent_status(user_id)
            
            if audit_result['compliance_status'] == 'action_required':
                self.handle_compliance_issue(user_id, audit_result['issues'])
        
        # Generate compliance report
        return generate_daily_compliance_report()
```

This privacy framework ensures full GDPR compliance while enabling the personalized nutrition coaching experience. The progressive consent model builds user trust while the comprehensive data rights implementation provides users with complete control over their information.
