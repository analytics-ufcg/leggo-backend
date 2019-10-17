# Generated by Django 2.2.6 on 2019-10-08 13:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0055_auto_20190816_1828'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='etapaproposicao',
            name='temperatura',
        ),
        migrations.AddField(
            model_name='etapaproposicao',
            name='id_leggo',
            field=models.IntegerField(default=1, help_text='Id interno do leggo.', verbose_name='ID Leggo'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='proposicao',
            name='id_leggo',
            field=models.IntegerField(default=1, help_text='Id interno do leggo.', verbose_name='ID do Leggo'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='temperaturahistorico',
            name='proposicao',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='temperatura_historico', to='api.Proposicao'),
        ),
    ]
