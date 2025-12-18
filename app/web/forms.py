"""WTForms for CSRF-protected forms."""
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DecimalField,
    EmailField,
    HiddenField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class LoginForm(FlaskForm):
    """Login form."""
    
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")


class ForgotPasswordForm(FlaskForm):
    """Password reset request form."""

    email = EmailField("Email", validators=[DataRequired(), Email()])


class ResetPasswordForm(FlaskForm):
    """Password reset form."""

    token = HiddenField("Token", validators=[DataRequired()])
    password = PasswordField("New Password", validators=[DataRequired(), Length(min=8)])
    password_confirm = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password")],
    )


class RegistrationForm(FlaskForm):
    """Tenant registration form."""
    
    tenant_name = StringField("Organization Name", validators=[DataRequired(), Length(max=255)])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    password_confirm = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    accept_terms = BooleanField("Accept Terms", validators=[DataRequired()])
