#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import cgi
import commands
import tempfile
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from webpay.models import OrdenCompraWebpay
from webpay.conf import *


@require_POST
@csrf_exempt
def compra_webpay(request):
    """
    Vista de Cierre de la compra que manejara la respuesta de Transbank.
    Es ejecutada por el CGI tbk_bp_resultado.cgi
    Recibira por metodo POST
    Validacion de MAC.
    Validacion de monto.
    Validacion de orden de compra.
    """
    resp = RECHAZADO_RESPONSE
    req = request
    qs = _get_order_params(req)
    orden_compra = req.POST.get('TBK_ORDEN_COMPRA')
    respuesta = req.POST.get('TBK_RESPUESTA')
    monto = int(req.POST.get('TBK_MONTO')) / 100
    codigo_autorizacion = req.POST.get('TBK_CODIGO_AUTORIZACION')
    id_transaccion = req.POST.get('TBK_ID_TRANSACCION')
    final_num_tarjeta = req.POST.get('TBK_FINAL_NUMERO_TARJETA')
    id_sesion = req.POST.get("TBK_ID_SESION")
    tipo_pago = req.POST.get("TBK_TIPO_PAGO")
    tipo_transaccion = req.POST.get("TBK_TIPO_TRANSACCION")
    fecha_contable = req.POST.get("TBK_FECHA_CONTABLE")
    #Comprueba archivo
    try:
        orden = OrdenCompraWebpay.objects.get(
            orden_compra=orden_compra)
        orden.id_transaccion = id_transaccion
        orden.codigo_transaccion = respuesta
        orden.codigo_autorizacion = codigo_autorizacion
        orden.final_num_tarjeta = final_num_tarjeta
        orden.id_sesion = id_sesion
        orden.codigo_autorizacion = codigo_autorizacion
        orden.fecha_transaccion = datetime.today()
        orden.tipo_pago = tipo_pago
        orden.tipo_transaccion = tipo_transaccion
        orden.fecha_contable = fecha_contable
    except OrdenCompraWebpay.DoesNotExist:
        raise
    if respuesta == "0":
        print monto, orden.monto
        if int(monto) == int(orden.monto):
            #Valida MAC
            if _valida_mac(qs) == VALID_MAC_RESPONSE:
                orden.status = STATUS["PAGADO"]
                resp = ACEPTADO_RESPONSE
            else:
                orden.status = STATUS["MAC_INVALIDO"]
        else:
            orden.status = STATUS["MONTO_INVALIDO"]
    else:
        orden.status = STATUS["RESP_INVALIDO"]
    orden.respuesta = resp
    orden.save()
    orden.enviar_signals()
    return HttpResponse(resp)

def _valida_mac(qs):
    """Funcion que validara la MAC que viene de resultado.cgi. Se debe generar
    un archivo de texto con los parametros recibidos en el formato en el que
    llegan, entregar la ubicacion del archivo
    """
    descriptor, temp_path = tempfile.mkstemp()
    f = os.fdopen(descriptor, "w")
    f.write(qs)
    f.close()
    command = "%(mac)s %(temp_path)s" % {
        "mac" : settings.URL_CGI_VALIDA_MAC,
        "temp_path": temp_path
    }
    valid_mac = commands.getoutput(command).strip() == VALID_MAC_RESPONSE
    print commands.getoutput(command).strip()
    os.remove(temp_path)
    return VALID_MAC_RESPONSE if valid_mac else RECHAZADO_RESPONSE

def _get_order_params(req):
    """Ordenar los parametros recibidos, separados con &"""
    return '&'.join(['%s=%s' % (k,v) for k,v in cgi.parse_qsl(req.body)])