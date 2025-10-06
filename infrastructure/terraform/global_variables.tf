# Global Infrastructure Variables
# Variables for international deployment and global services

# ===== TRANSLATION & LANGUAGE SERVICES =====

variable "enable_translation" {
  description = "Enable Amazon Translate for multi-language support"
  type        = bool
  default     = false
}

variable "supported_languages" {
  description = "List of language codes for translation support"
  type        = list(string)
  default     = ["es", "fr", "de", "pt", "ja", "ko", "zh", "ar", "hi", "it", "ru"]
}

variable "primary_language" {
  description = "Primary language code for the application"
  type        = string
  default     = "en"
}

# ===== TEXT-TO-SPEECH & VOICE SERVICES =====

variable "enable_polly" {
  description = "Enable Amazon Polly for text-to-speech"
  type        = bool
  default     = false
}

variable "polly_voices" {
  description = "Map of language codes to Polly voice IDs"
  type        = map(string)
  default = {
    "en" = "Joanna"
    "es" = "Lupe"
    "fr" = "Celine"
    "de" = "Marlene"
    "pt" = "Camila"
    "ja" = "Takumi"
    "ko" = "Seoyeon"
    "zh" = "Zhiyu"
    "ar" = "Zeina"
    "hi" = "Aditi"
    "it" = "Carla"
    "ru" = "Tatyana"
  }
}

# ===== NATURAL LANGUAGE PROCESSING =====

variable "enable_comprehend" {
  description = "Enable Amazon Comprehend for language detection and sentiment analysis"
  type        = bool
  default     = false
}

variable "comprehend_languages" {
  description = "List of language codes supported by Comprehend"
  type        = list(string)
  default     = ["en", "es", "fr", "de", "pt", "ja", "ko", "zh", "ar", "hi", "it"]
}

# ===== MULTI-REGION DEPLOYMENT =====

variable "enable_global_tables" {
  description = "Enable DynamoDB Global Tables for multi-region deployment"
  type        = bool
  default     = false
}

variable "global_table_regions" {
  description = "List of AWS regions for DynamoDB Global Tables"
  type        = list(string)
  default     = ["us-east-1", "eu-west-1", "ap-southeast-1"]
}

variable "enable_global_cloudfront" {
  description = "Enable global CloudFront distribution with multiple origins"
  type        = bool
  default     = false
}

variable "api_gateway_regions" {
  description = "List of regions where API Gateway is deployed"
  type        = list(string)
  default     = ["us-east-1", "eu-west-1", "ap-southeast-1"]
}

variable "primary_region" {
  description = "Primary AWS region for the application"
  type        = string
  default     = "us-east-1"
}

# ===== GEOGRAPHIC RESTRICTIONS =====

variable "geo_restriction_type" {
  description = "Type of geographic restriction (none, whitelist, blacklist)"
  type        = string
  default     = "none"
  validation {
    condition     = contains(["none", "whitelist", "blacklist"], var.geo_restriction_type)
    error_message = "Geo restriction type must be none, whitelist, or blacklist."
  }
}

variable "geo_restriction_countries" {
  description = "List of country codes for geographic restrictions"
  type        = list(string)
  default     = []
}

# ===== REGIONAL COMPLIANCE & DATA RESIDENCY =====

variable "enable_regional_encryption" {
  description = "Enable regional KMS keys for data residency compliance"
  type        = bool
  default     = false
}

variable "compliance_regions" {
  description = "List of regions requiring specific compliance measures"
  type        = list(string)
  default     = ["eu-west-1", "eu-central-1", "ca-central-1"]
}

variable "gdpr_regions" {
  description = "List of regions subject to GDPR compliance"
  type        = list(string)
  default     = ["eu-west-1", "eu-central-1", "eu-west-2", "eu-north-1"]
}

# ===== CULTURAL & DIETARY CONFIGURATIONS =====

variable "enable_cultural_support" {
  description = "Enable cultural and dietary restriction support"
  type        = bool
  default     = false
}

variable "cultural_configs" {
  description = "Cultural configurations for different regions"
  type = map(object({
    dietary_restrictions = list(string)
    food_preferences    = list(string)
    meal_timing        = map(string)
    cooking_methods    = list(string)
    religious_restrictions = list(string)
  }))
  default = {
    "middle_east" = {
      dietary_restrictions   = ["halal", "no_pork", "no_alcohol"]
      food_preferences      = ["lamb", "rice", "dates", "olive_oil", "legumes"]
      meal_timing          = {
        "breakfast" = "06:00-08:00"
        "lunch"     = "12:00-14:00"
        "dinner"    = "19:00-21:00"
        "iftar"     = "sunset"
        "suhoor"    = "pre-dawn"
      }
      cooking_methods       = ["grilling", "roasting", "stewing"]
      religious_restrictions = ["ramadan_fasting", "halal_certification"]
    }
    "south_asia" = {
      dietary_restrictions   = ["vegetarian_hindu", "no_beef", "no_pork", "jain_vegetarian"]
      food_preferences      = ["rice", "lentils", "curry", "spices", "vegetables"]
      meal_timing          = {
        "breakfast" = "07:00-09:00"
        "lunch"     = "12:00-14:00"
        "dinner"    = "19:00-21:00"
        "tea_time"  = "16:00-17:00"
      }
      cooking_methods       = ["curry", "steaming", "frying", "tandoor"]
      religious_restrictions = ["hindu_vegetarian", "jain_dietary_laws"]
    }
    "east_asia" = {
      dietary_restrictions   = ["low_dairy", "buddhist_vegetarian"]
      food_preferences      = ["rice", "noodles", "fish", "soy", "vegetables"]
      meal_timing          = {
        "breakfast" = "06:00-08:00"
        "lunch"     = "11:30-13:00"
        "dinner"    = "17:30-19:30"
      }
      cooking_methods       = ["stir_frying", "steaming", "braising", "grilling"]
      religious_restrictions = ["buddhist_dietary_laws"]
    }
    "mediterranean" = {
      dietary_restrictions   = ["mediterranean_diet"]
      food_preferences      = ["olive_oil", "fish", "vegetables", "grains", "legumes"]
      meal_timing          = {
        "breakfast" = "07:00-09:00"
        "lunch"     = "13:00-15:00"
        "dinner"    = "20:00-22:00"
        "siesta"    = "14:00-16:00"
      }
      cooking_methods       = ["grilling", "roasting", "braising"]
      religious_restrictions = ["orthodox_fasting"]
    }
    "kosher" = {
      dietary_restrictions   = ["kosher", "no_pork", "no_shellfish", "meat_dairy_separation"]
      food_preferences      = ["kosher_meat", "fish_with_scales", "kosher_wine"]
      meal_timing          = {
        "breakfast" = "07:00-09:00"
        "lunch"     = "12:00-14:00"
        "dinner"    = "18:00-20:00"
        "sabbath_prep" = "friday_before_sunset"
      }
      cooking_methods       = ["roasting", "braising", "kosher_prep"]
      religious_restrictions = ["kosher_certification", "sabbath_observance"]
    }
  }
}

# ===== GLOBAL MONITORING & ANALYTICS =====

variable "enable_global_monitoring" {
  description = "Enable global monitoring and analytics across regions"
  type        = bool
  default     = false
}

variable "global_alerting_channels" {
  description = "List of global alerting channels (email, slack, etc.)"
  type        = list(string)
  default     = []
}

# ===== TIMEZONE SUPPORT =====

variable "supported_timezones" {
  description = "List of supported timezones for global users"
  type        = list(string)
  default = [
    "America/New_York",     # EST/EDT
    "America/Chicago",      # CST/CDT
    "America/Denver",       # MST/MDT
    "America/Los_Angeles",  # PST/PDT
    "America/Toronto",      # Canada Eastern
    "America/Sao_Paulo",    # Brazil
    "Europe/London",        # GMT/BST
    "Europe/Paris",         # CET/CEST
    "Europe/Berlin",        # CET/CEST
    "Europe/Moscow",        # MSK
    "Asia/Tokyo",           # JST
    "Asia/Shanghai",        # CST
    "Asia/Kolkata",         # IST
    "Asia/Dubai",           # GST
    "Australia/Sydney",     # AEST/AEDT
    "Pacific/Auckland"      # NZST/NZDT
  ]
}

# ===== CURRENCY SUPPORT =====

variable "supported_currencies" {
  description = "Map of supported currencies with exchange rate sources"
  type = map(object({
    symbol          = string
    decimal_places  = number
    exchange_source = string
  }))
  default = {
    "USD" = { symbol = "$", decimal_places = 2, exchange_source = "federal_reserve" }
    "EUR" = { symbol = "€", decimal_places = 2, exchange_source = "ecb" }
    "GBP" = { symbol = "£", decimal_places = 2, exchange_source = "boe" }
    "JPY" = { symbol = "¥", decimal_places = 0, exchange_source = "boj" }
    "CAD" = { symbol = "C$", decimal_places = 2, exchange_source = "boc" }
    "AUD" = { symbol = "A$", decimal_places = 2, exchange_source = "rba" }
    "INR" = { symbol = "₹", decimal_places = 2, exchange_source = "rbi" }
    "BRL" = { symbol = "R$", decimal_places = 2, exchange_source = "bcb" }
    "CNY" = { symbol = "¥", decimal_places = 2, exchange_source = "pboc" }
    "KRW" = { symbol = "₩", decimal_places = 0, exchange_source = "bok" }
  }
}

# ===== MEASUREMENT SYSTEMS =====

variable "measurement_systems" {
  description = "Supported measurement systems by region"
  type = map(object({
    weight      = string  # kg, lbs
    volume      = string  # ml, oz
    temperature = string  # celsius, fahrenheit
    distance    = string  # km, miles
  }))
  default = {
    "metric" = {
      weight      = "kg"
      volume      = "ml"
      temperature = "celsius"
      distance    = "km"
    }
    "imperial" = {
      weight      = "lbs"
      volume      = "oz"
      temperature = "fahrenheit"
      distance    = "miles"
    }
  }
}

# ===== CONTENT DELIVERY =====

variable "enable_edge_locations" {
  description = "Enable CloudFront edge locations for global content delivery"
  type        = bool
  default     = true
}

variable "edge_location_price_class" {
  description = "CloudFront price class for edge locations"
  type        = string
  default     = "PriceClass_All"
  validation {
    condition     = contains(["PriceClass_100", "PriceClass_200", "PriceClass_All"], var.edge_location_price_class)
    error_message = "Edge location price class must be PriceClass_100, PriceClass_200, or PriceClass_All."
  }
}

# ===== REGIONAL PROVIDERS =====

variable "regional_providers" {
  description = "Configuration for regional AWS providers"
  type = map(object({
    region = string
    alias  = string
  }))
  default = {
    "us_east_1"      = { region = "us-east-1", alias = "us_east_1" }
    "eu_west_1"      = { region = "eu-west-1", alias = "eu_west_1" }
    "ap_southeast_1" = { region = "ap-southeast-1", alias = "ap_southeast_1" }
    "ap_northeast_1" = { region = "ap-northeast-1", alias = "ap_northeast_1" }
  }
}
