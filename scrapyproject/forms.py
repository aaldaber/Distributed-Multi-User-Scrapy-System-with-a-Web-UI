from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class CreateProject(forms.Form):
    projectname = forms.SlugField(label="Enter project name", max_length=50, required=True)
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.add_input(Submit('submit', 'Create Project'))
    helper.add_input(Submit('cancel', 'Cancel', css_class='btn-default'))


class DeleteProject(forms.Form):
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.add_input(Submit('submit', 'Confirm'))
    helper.add_input(Submit('cancel', 'Cancel', css_class='btn-default'))


class CreatePipeline(forms.Form):
    pipelinename = forms.SlugField(label="Pipeline name", max_length=50, required=True)
    pipelineorder = forms.IntegerField(label="Order", required=True, min_value=1, max_value=900)
    pipelinefunction = forms.CharField(label="Pipeline function:", required=False, widget=forms.Textarea)
    helper = FormHelper()
    helper.form_tag = False


class LinkGenerator(forms.Form):
    function = forms.CharField(label="Write your link generator function here:", required=False, widget=forms.Textarea)
    helper = FormHelper()
    helper.form_tag = False


class Scraper(forms.Form):
    function = forms.CharField(label="Write your scraper function here:", required=False, widget=forms.Textarea)
    helper = FormHelper()
    helper.form_tag = False


class ItemName(forms.Form):
    itemname = forms.SlugField(label="Enter item name", max_length=50, required=True)
    helper = FormHelper()
    helper.form_tag = False


class FieldName(forms.Form):
    fieldname = forms.SlugField(label="Field 1", max_length=50, required=False)
    extra_field_count = forms.CharField(widget=forms.HiddenInput())
    helper = FormHelper()
    helper.form_tag = False

    def __init__(self, *args, **kwargs):
        extra_fields = kwargs.pop('extra', 0)

        super(FieldName, self).__init__(*args, **kwargs)
        self.fields['extra_field_count'].initial = extra_fields

        for index in range(int(extra_fields)):
            # generate extra fields in the number specified via extra_fields
            self.fields['field_{index}'.format(index=index+2)] = forms.CharField(required=False)


class CreateDBPass(forms.Form):
    password = forms.CharField(label="Set the password for database access", max_length=200, required=True,
                               widget=forms.PasswordInput)
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.add_input(Submit('submit', 'Save'))
    helper.add_input(Submit('cancel', 'Cancel', css_class='btn-default'))


class Settings(forms.Form):
    settings = forms.CharField(required=False, widget=forms.Textarea)
    helper = FormHelper()
    helper.form_tag = False


class ShareDB(forms.Form):
    username = forms.CharField(label="Enter the account name for the user with whom you want to share the database", max_length=150, required=True)
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.add_input(Submit('submit', 'Share'))
    helper.add_input(Submit('cancel', 'Cancel', css_class='btn-default'))