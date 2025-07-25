# Generated by Django 5.2.4 on 2025-07-19 16:55

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('text', models.TextField()),
                ('embedding', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Answer',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('text', models.TextField()),
                ('confidence_score', models.FloatField(default=0.0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='qa.question')),
            ],
        ),
        migrations.CreateModel(
            name='RelevantChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('similarity_score', models.FloatField()),
                ('rank', models.IntegerField()),
                ('chunk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='documents.documentchunk')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='qa.question')),
            ],
            options={
                'ordering': ['rank'],
                'unique_together': {('question', 'chunk')},
            },
        ),
    ]
