"""WTForms for CSRF-protected forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, DecimalField, TextAreaField, SelectField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional


class LoginForm(FlaskForm):
    """Login form."""
    
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")


class RegistrationForm(FlaskForm):
    """Tenant registration form."""
    
    tenant_name = StringField("Organization Name", validators=[DataRequired(), Length(max=255)])
    tenant_slug = StringField("Subdomain", validators=[DataRequired(), Length(max=63)])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    password_confirm = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    accept_terms = BooleanField("Accept Terms", validators=[DataRequired()])
