"""WTForms for CSRF-protected forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, DecimalField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class LoginForm(FlaskForm):
    """Login form."""
    
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])


class RegistrationForm(FlaskForm):
    """Tenant registration form."""
    
    tenant_name = StringField("Organization Name", validators=[DataRequired(), Length(max=255)])
    subdomain = StringField("Subdomain", validators=[DataRequired(), Length(max=63)])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
