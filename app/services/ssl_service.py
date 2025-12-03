import ssl
import socket
from datetime import datetime, timezone
from typing import Optional, Dict
from urllib.parse import urlparse
import OpenSSL


def get_ssl_certificate(hostname: str, port: int = 443, timeout: int = 10) -> Optional[Dict]:
    """
    Check SSL certificate for a domain and return certificate information.
    
    Returns:
        Dict with certificate info or None if SSL check fails
    """
    original_hostname = hostname
    try:
        # Parse hostname if it's a full URL
        if hostname.startswith(('http://', 'https://')):
            parsed = urlparse(hostname)
            hostname = parsed.netloc or parsed.path
        
        hostname = hostname.strip()
        
        # Remove port if included in hostname
        if ':' in hostname:
            hostname = hostname.split(':')[0]
        
        # Remove IPv6 brackets
        if hostname.startswith('[') and hostname.endswith(']'):
            hostname = hostname[1:-1]
        
        # Validate hostname - must contain at least one dot (basic validation)
        if '.' not in hostname:
            print(f"❌ Invalid hostname format: {hostname} (must be a valid domain like example.com)")
            return {
                'valid': False,
                'hostname': original_hostname,
                'error': f'Invalid hostname: "{hostname}" is not a valid domain. Use format like "example.com" or "https://example.com"',
                'checked_at': datetime.now(timezone.utc)
            }
        
        print(f"🔍 Checking SSL for: {hostname}")
        
        # Create SSL context with better defaults
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        
        # Connect and get certificate
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as secure_sock:
                # Get certificate in DER format
                cert_der = secure_sock.getpeercert(binary_form=True)
                
                # Convert to OpenSSL certificate object for detailed info
                cert = OpenSSL.crypto.load_certificate(
                    OpenSSL.crypto.FILETYPE_ASN1,
                    cert_der
                )
                
                # Get certificate details
                subject_components = cert.get_subject().get_components()
                issuer_components = cert.get_issuer().get_components()
                
                # Safely extract subject and issuer
                subject = {}
                for key, value in subject_components:
                    subject[key] = value
                    
                issuer = {}
                for key, value in issuer_components:
                    issuer[key] = value
                
                # Parse expiration date
                expiry_date_str = cert.get_notAfter().decode('ascii')
                expiry_date = datetime.strptime(expiry_date_str, '%Y%m%d%H%M%SZ')
                expiry_date = expiry_date.replace(tzinfo=timezone.utc)
                
                # Calculate days until expiry
                now = datetime.now(timezone.utc)
                days_until_expiry = (expiry_date - now).days
                
                print(f"✅ SSL check successful for {hostname}: {days_until_expiry} days until expiry")
                
                return {
                    'valid': True,
                    'hostname': hostname,
                    'expiry_date': expiry_date,
                    'days_until_expiry': days_until_expiry,
                    'issuer': issuer.get(b'O', b'Unknown').decode('utf-8'),
                    'subject': subject.get(b'CN', b'Unknown').decode('utf-8'),
                    'serial_number': str(cert.get_serial_number()),
                    'version': cert.get_version(),
                    'checked_at': now
                }
    except ssl.SSLError as e:
        print(f"❌ SSL Error for {hostname}: {str(e)}")
        return {
            'valid': False,
            'hostname': hostname,
            'error': f'SSL Error: {str(e)}',
            'checked_at': datetime.now(timezone.utc)
        }
    except socket.gaierror as e:
        print(f"❌ DNS Error for {hostname}: {str(e)}")
        return {
            'valid': False,
            'hostname': hostname,
            'error': f'DNS Error: {str(e)}',
            'checked_at': datetime.now(timezone.utc)
        }
    except socket.timeout:
        print(f"❌ Timeout checking SSL for {hostname}")
        return {
            'valid': False,
            'hostname': hostname,
            'error': 'Connection timeout',
            'checked_at': datetime.now(timezone.utc)
        }
    except Exception as e:
        print(f"❌ Unexpected error checking SSL for {hostname}: {str(e)}")
        return {
            'valid': False,
            'hostname': hostname,
            'error': str(e),
            'checked_at': datetime.now(timezone.utc)
        }


def should_alert_ssl_expiry(days_until_expiry: int) -> tuple[bool, str]:
    """
    Determine if SSL expiry should trigger an alert.
    
    Returns:
        Tuple of (should_alert, severity_level)
    """
    if days_until_expiry <= 0:
        return True, 'critical'  # Expired
    elif days_until_expiry <= 7:
        return True, 'critical'  # 7 days or less
    elif days_until_expiry <= 30:
        return True, 'warning'  # 30 days or less
    elif days_until_expiry <= 60:
        return True, 'info'  # 60 days or less
    
    return False, 'normal'


def format_ssl_alert_message(domain_name: str, days_until_expiry: int, expiry_date: datetime) -> str:
    """
    Format SSL expiry alert message.
    """
    if days_until_expiry <= 0:
        return f"🔴 SSL EXPIRED: {domain_name} certificate has EXPIRED!"
    elif days_until_expiry == 1:
        return f"🔴 SSL EXPIRING: {domain_name} certificate expires in 1 day!"
    elif days_until_expiry <= 7:
        return f"🟠 SSL WARNING: {domain_name} certificate expires in {days_until_expiry} days"
    elif days_until_expiry <= 30:
        return f"🟡 SSL NOTICE: {domain_name} certificate expires in {days_until_expiry} days"
    else:
        return f"ℹ️ SSL INFO: {domain_name} certificate expires in {days_until_expiry} days"
