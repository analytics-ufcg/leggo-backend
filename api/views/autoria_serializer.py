from rest_framework import serializers, generics
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.db.models import (
    F,
    Count,
    Prefetch,
    Value,
    CharField,
    Sum,
    Max,
    Min,
    FloatField)
from django.db.models.expressions import Window
from django.db.models.functions import Concat, ExtractYear
from django.db.models.functions.window import RowNumber

from api.model.autoria import Autoria
from api.utils.filters import get_filtered_interesses


class AutoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Autoria
        fields = (
            "id_leggo",
            "id_documento",
            "id_autor",
            "descricao_tipo_documento",
            "data",
            "url_inteiro_teor",
            "autores",
        )


class AutoriaList(generics.ListAPIView):
    """
    Dados de autoria de uma proposição. Apresenta lista de documentos contendo informações
    como a data de apresentação, tipo e autores.
    """

    serializer_class = AutoriaSerializer

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                "id da proposição no sistema do Leg.go",
                type=openapi.TYPE_INTEGER,
            ),
        ]
    )
    def get_queryset(self):
        """
        Retorna a autoria
        """
        id_prop = self.kwargs["id"]
        return Autoria.objects.filter(id_leggo=id_prop)


class AutoriaAutorSerializer(serializers.Serializer):
    id_autor_parlametria = serializers.IntegerField()
    id_documento = serializers.IntegerField()
    id_leggo = serializers.CharField()
    data = serializers.DateField()
    descricao_tipo_documento = serializers.CharField()
    url_inteiro_teor = serializers.CharField()
    tipo_documento = serializers.CharField()
    tipo_acao = serializers.CharField()
    peso_autor_documento = serializers.FloatField()
    sigla = serializers.CharField()


class AutoriasAutorList(generics.ListAPIView):
    """
    Informações sobre autorias de um autor específico.
    """

    serializer_class = AutoriaAutorSerializer

    def get_queryset(self):
        '''
        Retorna as autorias de um parlamentar.
        Se não for passado um interesse como argumento,
        os dados retornados serão os do interesse default (leggo).
        '''
        interesse_arg = self.request.query_params.get('interesse')
        tema_arg = self.request.query_params.get('tema')
        if interesse_arg is None:
            interesse_arg = 'leggo'
        interesses = get_filtered_interesses(interesse_arg, tema_arg)
        id_autor_arg = self.kwargs['id_autor']
        autorias = (
            Autoria.objects
            .filter(id_leggo__in=interesses.values('id_leggo'),
                    id_autor_parlametria=id_autor_arg,
                    data__gte='2019-01-31')
            .select_related('etapa_proposicao')
            .values('id_autor_parlametria', 'id_documento', 'id_leggo',
                    'data', 'descricao_tipo_documento', 'url_inteiro_teor',
                    'tipo_documento', 'tipo_acao', 'peso_autor_documento',
                    'etapa_proposicao__sigla_tipo',
                    'etapa_proposicao__numero',
                    'etapa_proposicao__data_apresentacao')
            .annotate(
                sigla=Concat(
                    'etapa_proposicao__sigla_tipo', Value(' '),
                    'etapa_proposicao__numero', Value('/'),
                    ExtractYear('etapa_proposicao__data_apresentacao'),
                    output_field=CharField())
                )
        )

        return autorias


class AutoriasAgregadasSerializer(serializers.Serializer):
    id_autor = serializers.IntegerField()
    id_autor_parlametria = serializers.IntegerField()
    quantidade_autorias = serializers.IntegerField()
    peso_documentos = serializers.FloatField()
    min_peso_documentos = serializers.FloatField()
    max_peso_documentos = serializers.FloatField()


class AutoriasAgregadasList(generics.ListAPIView):
    """
    Informação agregada sobre autorias de projetos de lei
    """

    serializer_class = AutoriasAgregadasSerializer

    def get_queryset(self):
        '''
        Retorna quantidade de autorias por parlamentar.
        Se não for passado um interesse como argumento,
        os dados retornados serão os do interesse default (leggo).
        '''
        interesse_arg = self.request.query_params.get('interesse')
        tema_arg = self.request.query_params.get('tema')
        if interesse_arg is None:
            interesse_arg = 'leggo'
        interesses = get_filtered_interesses(interesse_arg, tema_arg)

        autorias = (
            Autoria.objects
            .filter(id_leggo__in=interesses.values('id_leggo'),
                    data__gte='2019-01-31',
                    tipo_acao__in=['Proposição', 'Recurso'])
            .values('id_autor', 'id_autor_parlametria')
            .annotate(quantidade_autorias=Count('id_autor'))
            .prefetch_related(
                Prefetch("interesse", queryset=interesses)
            )
            .values("id_autor", "id_autor_parlametria")
            .annotate(
                quantidade_autorias=Count("id_autor"),
                peso_documentos=Sum("peso_autor_documento"))
            .prefetch_related(Prefetch("interesse", queryset=interesses))
        )

        min_max = autorias.aggregate(
                max_peso_documentos=Max("peso_documentos"),
                min_peso_documentos=Min("peso_documentos"))
        autorias = autorias.annotate(
                max_peso_documentos=Value(min_max["max_peso_documentos"], FloatField()),
                min_peso_documentos=Value(min_max["min_peso_documentos"], FloatField())
            )

        return autorias


class AutoriasAgregadasByAutor(generics.ListAPIView):
    """
    Informação agregada sobre autorias de projetos de lei
    para um autor específico passado como parâmetro
    """

    serializer_class = AutoriasAgregadasSerializer

    def get_queryset(self):
        '''
        Retorna quantidade de autorias para um parlamentar específico.
        Considera as autorias do parlamentar para um interesse específico.
        Se não for passado um interesse como argumento,
        os dados retornados serão os do interesse default (leggo).
        '''
        interesse_arg = self.request.query_params.get('interesse')
        tema_arg = self.request.query_params.get('tema')
        if interesse_arg is None:
            interesse_arg = 'leggo'
        interesses = get_filtered_interesses(interesse_arg, tema_arg)

        id_autor_parlametria = self.kwargs["id_autor"]

        autorias = (
            Autoria.objects.filter(
                id_leggo__in=interesses.values('id_leggo'),
                data__gte='2019-01-31',
                tipo_acao__in=['Proposição', 'Recurso'])
            .values("id_autor", "id_autor_parlametria")
            .annotate(
                quantidade_autorias=Count("id_autor"),
                peso_documentos=Sum("peso_autor_documento"))
            .prefetch_related(Prefetch("interesse", queryset=interesses))
        )

        min_max = autorias.aggregate(
                max_peso_documentos=Max("peso_documentos"),
                min_peso_documentos=Min("peso_documentos"))
        autorias = autorias.filter(id_autor_parlametria=id_autor_parlametria).annotate(
                max_peso_documentos=Value(min_max["max_peso_documentos"], FloatField()),
                min_peso_documentos=Value(min_max["min_peso_documentos"], FloatField())
            )

        return autorias


class AcoesSerializer(serializers.Serializer):
    id_autor_parlametria = serializers.IntegerField()
    num_documentos = serializers.IntegerField()
    ranking_documentos = serializers.IntegerField()
    peso_total = serializers.FloatField()
    tipo_acao = serializers.CharField()


class Acoes(generics.ListAPIView):
    """
    Dados de ações de um parlamentar. Apresenta números de emendas e requerimentos,
    assim como sua posição no ranking.
    """

    serializer_class = AcoesSerializer

    def get_queryset(self):
        '''
        Retorna as ações do parlamentar
        '''
        interesse_arg = self.request.query_params.get('interesse')
        tema_arg = self.request.query_params.get('tema')
        if interesse_arg is None:
            interesse_arg = 'leggo'
        interesses = get_filtered_interesses(interesse_arg, tema_arg)
        autores = (
            Autoria.objects
            .filter(id_leggo__in=interesses.values('id_leggo'),
                    data__gte='2019-01-31')
        )

        result = (
            autores.values('id_autor_parlametria', 'tipo_acao')
            .annotate(num_documentos=Count('tipo_acao'))
            .annotate(peso_total=Sum('peso_autor_documento'))
            .annotate(ranking_documentos=Window(
                expression=RowNumber(),
                partition_by=[F('tipo_acao')],
                order_by=F('peso_total').desc()))
            .order_by('ranking_documentos', 'tipo_acao')
        )

        return result


class AutoriasOriginaisSerializer(serializers.Serializer):
    id_autor_parlametria = serializers.IntegerField()
    id_documento = serializers.IntegerField()
    id_leggo = serializers.CharField()
    data = serializers.DateField()
    descricao_tipo_documento = serializers.CharField()
    url_inteiro_teor = serializers.CharField()
    tipo_documento = serializers.CharField()
    tipo_acao = serializers.CharField()
    sigla = serializers.CharField()


class AutoriasOriginaisList(generics.ListAPIView):
    '''
    Informações sobre proposições originais ou apensadas de um autor específico.
    '''
    serializer_class = AutoriasOriginaisSerializer

    def get_queryset(self):
        '''
        Retorna as proposições originais ou apensadas de um parlamentar.
        Se não for passado um interesse como argumento,
        os dados retornados serão os do interesse default (leggo).
        '''
        interesse_arg = self.request.query_params.get('interesse')
        tema_arg = self.request.query_params.get('tema')
        if interesse_arg is None:
            interesse_arg = 'leggo'
        interesses = get_filtered_interesses(interesse_arg, tema_arg)

        id_autor_arg = self.kwargs['id_autor']

        autorias = (
            Autoria.objects
            .filter(id_leggo__in=interesses.values('id_leggo'),
                    id_autor_parlametria=id_autor_arg,
                    data__gte='2019-01-31',
                    tipo_documento='Prop. Original / Apensada')
            .select_related('etapa_proposicao')
            .values('id_autor_parlametria', 'id_documento', 'id_leggo',
                    'data', 'descricao_tipo_documento', 'url_inteiro_teor',
                    'tipo_documento', 'tipo_acao', 'etapa_proposicao__sigla_tipo',
                    'etapa_proposicao__numero',
                    'etapa_proposicao__data_apresentacao')
            .annotate(
                sigla=Concat(
                    'etapa_proposicao__sigla_tipo', Value(' '),
                    'etapa_proposicao__numero', Value('/'),
                    ExtractYear('etapa_proposicao__data_apresentacao'),
                    output_field=CharField())
            )
        )

        return autorias


class AutoriasTabelaSerializer(serializers.Serializer):
    id_autor = serializers.IntegerField()
    casa_autor = serializers.CharField()
    id_documento = serializers.IntegerField()
    id_leggo = serializers.CharField()
    id_principal = serializers.CharField()
    casa = serializers.CharField()
    data = serializers.DateField()
    descricao_tipo_documento = serializers.CharField()
    tipo_documento = serializers.CharField()
    tipo_acao = serializers.CharField()
    peso_autor_documento = serializers.FloatField()


class AutoriasTabelaList(generics.ListAPIView):
    """
    Informações sobre autorias de documentos relacionadas a projetos
    """

    serializer_class = AutoriasTabelaSerializer

    def get_queryset(self):
        '''
        Retorna as autorias dos parlamentares
        Se não for passado um interesse como argumento,
        os dados retornados serão os do interesse default (leggo).
        '''
        interesse_arg = self.request.query_params.get('interesse')
        tema_arg = self.request.query_params.get('tema')

        if interesse_arg is None:
            interesse_arg = 'leggo'
        interesses = get_filtered_interesses(interesse_arg, tema_arg)

        autorias = (
            Autoria.objects
            .filter(id_leggo__in=interesses.values('id_leggo'),
                    data__gt='2019-01-31')
            .select_related('etapa_proposicao')
            .values('id_autor', 'casa_autor', 'id_documento', 'id_leggo',
                    'id_principal', 'casa',
                    'data', 'descricao_tipo_documento',
                    'tipo_documento', 'tipo_acao', 'peso_autor_documento',
                    'etapa_proposicao__sigla_tipo',
                    'etapa_proposicao__numero',
                    'etapa_proposicao__data_apresentacao')
        )

        return autorias
