# LIGARS-CORE: AI-Driven Personality Simulation Framework

## Overview

**LIGARS-CORE** is an advanced AI-driven framework engineered for sophisticated personality simulation, psychological profiling, and immersive storytelling experiences. Built on cutting-edge machine learning and natural language processing technologies, LIGARS-CORE enables developers to construct dynamic, context-aware narrative systems with realistic character interactions and behavioral modeling.

The framework operates on principles of computational psychology, leveraging generative AI to simulate complex personality matrices within fictional scenarios, enabling comprehensive motivation testing and character development analysis.

## Key Features

- **Personality Simulation Engine**: Advanced algorithms for realistic character behavior modeling
- **Psychological Profiling**: Comprehensive psychometric analysis within narrative contexts
- **Encrypted Credential Management**: AES-256 encryption for secure SMTP credential storage
- **Modular Architecture**: Flexible, extensible design for custom implementations
- **Multi-Platform Support**: Native Linux support with cross-platform compatibility

## Installation

### Automated Installation (Linux)

Execute the automated installation script:

```bash
chmod +x install_ligars.sh
./install_ligars.sh
```

This script will automatically:
- Verify Python 3.8+ availability
- Create an isolated Python virtual environment
- Install all required dependencies
- Generate a template configuration file

### Manual Installation

For advanced users or custom configurations:

```bash
# Create virtual environment
python3 -m venv venv_ligars
source venv_ligars/bin/activate

# Install dependencies
pip install --upgrade pip
pip install flask requests google-generativeai cryptography
```

### Configuration Setup

1. **Create Configuration File**

Create a `config.json` file in your project root:

```json
{
  "ai_model": "gemini-pro",
  "simulation_mode": "standard",
  "encryption_enabled": true,
  "smtp": {
    "server": "smtp.example.com",
    "port": 587,
    "username": "your_email@example.com"
  },
  "logging_level": "INFO"
}
```

2. **Set Environment Variables**

Configure the `LIGARS_MASTER_KEY` for encrypted credential storage:

```bash
echo "export LIGARS_MASTER_KEY='your_secure_encryption_key_min_32_chars'" >> ~/.bashrc
```

Add this to your shell profile (`~/.bashrc`, `~/.zshrc`, or `~/.bash_profile`) for persistence:

```bash
echo "export LIGARS_MASTER_KEY='your_secure_encryption_key'" >> ~/.bashrc
source ~/.bashrc
```

## Security Architecture

### Credential Protection

- **Zero Trust Principle**: No private keys, API credentials, or sensitive data are stored in the repository
- **AES-256 Encryption**: SMTP passwords and sensitive configuration data are encrypted using AES-256-CBC
- **Key Derivation**: Master keys are derived using PBKDF2 with SHA-256 hashing
- **Local Secrets Management**: All credentials managed exclusively through environment variables and local configuration files

### Best Practices

```bash
# NEVER commit credentials or the LIGARS_MASTER_KEY
echo "config.json" >> .gitignore
echo ".env" >> .gitignore

# Verify your key has sufficient entropy
echo -n "your_key" | wc -c  # Should be at least 32 characters
```

## Dependencies

- **flask** (2.0+): Lightweight web framework for API endpoints
- **requests**: HTTP client library for external API communication
- **google-generativeai**: Google's generative AI API integration
- **cryptography**: Industry-standard encryption library for credential management

## Architecture

```
ligars-core/
├── venv_ligars/           # Python virtual environment
├── config.json            # Configuration template (user-created)
├── install_ligars.sh      # Automated installation script
├── core/                  # Core simulation engine
├── models/                # Personality and behavioral models
└── utils/                 # Encryption and utility modules
```

## Usage Example

```python
from ligars_core import SimulationEngine, EncryptionManager

# Initialize encryption manager
encryption_mgr = EncryptionManager()

# Load configuration
config = encryption_mgr.load_config('config.json')

# Initialize simulation engine
engine = SimulationEngine(config)

# Execute personality simulation
results = engine.simulate_scenario(profile_data, context)
```

## Contributing

Contributions to LIGARS-CORE are welcome. Please ensure:
- All code adheres to security best practices
- Sensitive data handling is properly documented
- Pull requests include comprehensive testing

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support & Contact

For technical inquiries, bug reports, or feature requests, please open an issue on the GitHub repository.

---

**Disclaimer**: LIGARS-CORE is designed for educational, research, and creative development purposes. Users are responsible for ensuring compliance with applicable laws and ethical guidelines in their jurisdiction.