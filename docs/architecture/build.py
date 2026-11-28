"""Build the editable mxGraph diagram and its matching visual exports."""
from html import escape
from pathlib import Path
import os
import subprocess
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


OUT = Path(__file__).resolve().parent
STEM = OUT / 'MineSight_Architecture'
W, H = 1500, 1194
INK, GRAY, COPPER, BLUE = '#0F172A', '#475569', '#C27035', '#2563EB'
WHITE = '#FFFFFF'
font_dir = Path(os.environ.get('WINDIR', '/usr/share/fonts/truetype/liberation2'))
if os.name == 'nt':
    font_dir /= 'Fonts'
    font_files = ('arial.ttf', 'arialbd.ttf')
else:
    font_files = ('LiberationSans-Regular.ttf', 'LiberationSans-Bold.ttf')
for name, file in zip(('Diagram', 'DiagramBold'), font_files):
    pdfmetrics.registerFont(TTFont(name, str(font_dir / file)))


def build(pdf):
    file = ET.Element('mxfile', host='app.diagrams.net')
    diagram = ET.SubElement(file, 'diagram', id='minesight', name='Arquitectura MineSight')
    model = ET.SubElement(diagram, 'mxGraphModel', grid='1', gridSize='10',
                          page='1', pageScale='1', pageWidth=str(W), pageHeight=str(H),
                          background=WHITE, arrows='1', connect='1')
    root = ET.SubElement(model, 'root')
    ET.SubElement(root, 'mxCell', id='0')
    ET.SubElement(root, 'mxCell', id='1', parent='0')
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img"><title>MineSight — Arquitectura del sistema</title><rect width="100%" height="100%" fill="#fff"/>']
    c = Canvas(str(pdf), pagesize=(W, H))
    bounds = {'1': (0, 0, W, H)}

    def vertex(key, value, x, y, w, h, style, parent):
        node = ET.SubElement(root, 'mxCell', id=key, value=value,
                             vertex='1', parent=parent, style=style)
        px, py, pw, ph = bounds[parent]
        assert px <= x and py <= y and x+w <= px+pw and y+h <= py+ph, key
        ET.SubElement(node, 'mxGeometry', x=str(x-px), y=str(y-py),
                      width=str(w), height=str(h), attrib={'as': 'geometry'})
        bounds[key] = x, y, w, h

    def rect(key, x, y, w, h, fill, stroke, parent='1', radius=12):
        vertex(key, '', x, y, w, h, f'rounded=1;absoluteArcSize=1;arcSize={radius*2};'
               f'fillColor={fill};strokeColor={stroke};container=1;recursiveResize=0;',
               parent)
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>')
        c.setFillColor(fill)
        c.setStrokeColor(stroke)
        c.roundRect(x, H-y-h, w, h, radius, fill=1, stroke=1)

    def label(key, x, y, value, size=18, color=INK, bold=False, parent='1', width=None):
        lines = value.split('\n')
        font = 'DiagramBold' if bold else 'Diagram'
        measured = max(pdfmetrics.stringWidth(line, font, size) for line in lines)
        width = width or int(measured)+7
        assert measured <= width, (key, measured, width)
        step = round(size*1.22)
        vertex(key, value, x, y, width, step*len(lines)+3,
               f'text;html=0;align=left;verticalAlign=top;spacing=0;whiteSpace=nowrap;'
               f'fontFamily=Arial;fontSize={size};fontColor={color};fontStyle={int(bold)};'
               'fillColor=none;strokeColor=none;resizable=0;', parent)
        c.setFont(font, size)
        c.setFillColor(color)
        for n, line in enumerate(lines):
            baseline = y+size+n*step
            svg.append(f'<text x="{x}" y="{baseline}" font-family="Arial, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(line)}</text>')
            c.drawString(x, H-baseline, line)

    def icon(key, x, y, parent):
        vertex(key, '', x, y, 24, 29, 'shape=document;fillColor=#FFF7ED;'
               'strokeColor=#A15124;strokeWidth=1.5;', parent)
        svg.append(f'<path d="M{x},{y} h24 v24 q-6,-4 -12,0 t-12,0 z" fill="#FFF7ED" stroke="#A15124" stroke-width="1.5"/>')
        c.setFillColor('#FFF7ED')
        c.setStrokeColor('#A15124')
        p = c.beginPath()
        p.moveTo(x, H-y)
        p.lineTo(x+24, H-y)
        p.lineTo(x+24, H-y-24)
        p.curveTo(x+16, H-y-18, x+8, H-y-30, x, H-y-24)
        p.close()
        c.drawPath(p, fill=1, stroke=1)

    def line(points, color, dashed=False, head=True):
        dash = ' stroke-dasharray="7 5"' if dashed else ''
        svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in points)+
                   f'" fill="none" stroke="{color}" stroke-width="2.3"{dash}/>')
        c.setStrokeColor(color)
        c.setLineWidth(2.3)
        c.setDash([7, 5] if dashed else [])
        for (x,y), (tx,ty) in zip(points, points[1:]):
            assert x == tx or y == ty
            c.line(x,H-y,tx,H-ty)
        if head:
            (px, py), (x, y) = points[-2:]
            dx = 9 if x > px else -9 if x < px else 0
            dy = 9 if y > py else -9 if y < py else 0
            vertices = [(x,y),(x-dx+.53*dy,y-dy-.53*dx),(x-dx-.53*dy,y-dy+.53*dx)]
            svg.append('<polygon points="'+' '.join(f'{a},{b}' for a,b in vertices)+f'" fill="{color}"/>')
            c.setFillColor(color)
            path = c.beginPath()
            path.moveTo(x,H-y)
            for a,b in vertices[1:]:
                path.lineTo(a,H-b)
            path.close()
            c.drawPath(path, fill=1, stroke=0)
        c.setDash([])

    def edge(key, source, target, points, color, dashed=False):
        def anchor(which, cell, point):
            x,y,w,h = bounds[cell]
            px,py = point
            assert (px in (x,x+w) and y <= py <= y+h) or (py in (y,y+h) and x <= px <= x+w)
            return f'{which}X={(px-x)/w};{which}Y={(py-y)/h};{which}Dx=0;{which}Dy=0;{which}Perimeter=0;'

        style = ('edgeStyle=orthogonalEdgeStyle;rounded=0;endArrow=block;endFill=1;'
                 f'strokeColor={color};strokeWidth=2.3;dashed={int(dashed)};dashPattern=7 5;'
                 +anchor('exit',source,points[0])+anchor('entry',target,points[-1]))
        cell = ET.SubElement(root,'mxCell',id=key,edge='1',parent='1',source=source,target=target,style=style)
        geometry = ET.SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})
        if len(points) > 2:
            array = ET.SubElement(geometry,'Array',attrib={'as':'points'})
            for x,y in points[1:-1]:
                ET.SubElement(array,'mxPoint',x=str(x),y=str(y))
        line(points, color, dashed)

    def layer(key, y, h, heading, side, fill, border, accent):
        rect(key, 35, y, 1430, h, fill, border, radius=17)
        label(key+'-title',57,y+15,heading,23,accent,True,key)
        label(key+'-context',1090,y+20,side,17,GRAY,False,key)

    def card(key, parent, x, y, w, h, title, body, accent, stroke='#CBD5E1', file_icon=False):
        rect(key,x,y,w,h,WHITE,stroke,parent)
        if file_icon:
            icon(key+'-icon',x+14,y+16,key)
        tx = x+(48 if file_icon else 15)
        label(key+'-title',tx,y+12,title,19,accent,True,key,width=x+w-10-tx)
        label(key+'-body',tx,y+43,body,15 if parent == 'offline' else 17,GRAY,False,key,width=x+w-10-tx)

    label('eyebrow',35,26,'Machine Learning · Proyecto Final · UPCH 2026-II',18,'#93471E',True)
    label('title',35,55,'MineSight — Arquitectura del sistema',42,INK,True)
    label('subtitle',36,115,'Segmentación inteligente de operaciones de flotación minera mediante aprendizaje no supervisado.',21,GRAY)

    layer('offline',164,217,'01   Entrenamiento offline | Kaggle','Python · pandas · scikit-learn','#FFFAF5','#E5C7AF','#93471E')
    offline = [
        ('source','Dataset de flotación','CSV público de Kaggle\n737 453 registros\n24 columnas'),
        ('prepare','Preparación','Conversión de tipos\nLimpieza y deduplicación\nPromedios por hora'),
        ('features','Variables y escala','7 variables operativas\n4 097 horas de análisis\nStandardScaler'),
        ('models','Clustering','K-Means con k de 2 a 8\nMiniBatch K-Means\nComparación con k=7'),
        ('evaluate','Evaluación','Silhouette, inercia, DB y CH\nARI entre semillas\nPerfiles y PCA (2D)'),
        ('select','Modelo final','K-Means con k=7\nSilhouette 0,2262\nARI medio 0,9959'),
    ]
    for i, (key,title,body) in enumerate(offline):
        card(key,'offline',56+234*i,226,216,120,title,body,'#93471E','#DFC0A7')
    for i in range(len(offline)-1):
        x = 56+234*i
        edge(f'train-{i}',offline[i][0],offline[i+1][0],[(x+216,285),(x+234,285)],COPPER)
    label('metrics-note',57,353,'DB: Davies–Bouldin · CH: Calinski–Harabasz · ARI: Adjusted Rand Index',15,GRAY,False,'offline')

    layer('artifacts',419,164,'02   Persistencia de artefactos ML','Repositorio · models/ · joblib','#F8FAFC','#CBD5E1',INK)
    card('kmeans','artifacts',56,469,307,90,'Modelo entrenado','minesight_kmeans.pkl',INK,file_icon=True)
    card('scaler','artifacts',384,469,307,90,'Escalador ajustado','minesight_scaler.pkl',INK,file_icon=True)
    card('order','artifacts',712,469,307,90,'Orden de las 7 variables','minesight_variables.pkl',INK,file_icon=True)
    card('bundle','artifacts',1040,469,402,90,'Artefactos versionados','Tres archivos PKL del notebook',INK)
    edge('persist','select','bundle',[(1334,346),(1334,469)],COPPER,True)
    label('persist-label',1346,386,'Exportación PKL',14,'#93471E',True)

    layer('production',634,254,'03   Aplicación web | Producción','Next.js y FastAPI','#EFF6FF','#BFDBFE','#1D4ED8')
    card('user','production',56,687,247,168,'Usuario final','Ingresa 7 valores\nCarga un archivo CSV\nConsulta perfiles y gráficos',INK,'#BFDBFE')
    card('frontend','production',423,687,337,168,'Next.js | Vercel','Panel histórico y ficha del modelo\nFormulario y vista previa del CSV\nVisualización de segmentos y PCA\nDescarga de resultados',INK,'#BFDBFE')
    rect('backend',949,687,493,168,WHITE,'#BFDBFE','production')
    label('backend-title',964,699,'FastAPI | Render',19,INK,True,'backend')
    label('backend-steps',964,730,'Validación CSV y JSON\nAgregación horaria opcional\nEscalador original\nInferencia con K-Means',17,GRAY,False,'backend')
    label('outputs-title',1211,699,'Resultados de la API',19,INK,True,'backend')
    label('outputs',1211,730,'Clúster y distancias¹\nPerfiles y PCA opcional²\nCSV y reporte Markdown',17,GRAY,False,'backend')
    edge('load','bundle','backend',[(1334,559),(1334,687)],COPPER,True)
    label('load-label',961,594,'Carga al iniciar la API · verificación SHA-256',16,'#93471E',True)
    edge('user-request','user','frontend',[(303,743),(423,743)],BLUE)
    edge('user-response','frontend','user',[(423,807),(303,807)],BLUE)
    label('user-request-label',321,714,'Datos / CSV',15,'#1D4ED8',True)
    label('user-response-label',327,778,'Resultados',15,'#1D4ED8',True)
    edge('api-request','frontend','backend',[(760,743),(949,743)],BLUE)
    edge('api-response','backend','frontend',[(949,807),(760,807)],BLUE)
    label('api-request-label',782,714,'HTTPS · JSON o CSV',15,'#1D4ED8',True)
    label('api-response-label',774,778,'HTTPS · JSON o archivo',15,'#1D4ED8',True)
    label('result-note',56,861,'¹ Distancias a los centroides en predicción manual.  ² PCA del lote cuando hay variación suficiente.',15,GRAY,False,'production')
    label('inference-note',1129,861,'Inferencia sin reentrenamiento',15,'#1D4ED8',True,'production')

    layer('contract',910,218,'04   Contrato HTTP y procesamiento','FastAPI · /api · CORS','#F8FAFC','#CBD5E1',INK)
    card('routes','contract',56,965,378,149,'Rutas de la API',
         'GET /health · /model-info\nPOST /predict · /preview-csv\nPOST /analyze-csv\nPOST /export-csv/{kind}',INK)
    card('validation','contract',450,965,300,149,'Validación de entradas',
         'JSON tipado con Pydantic\nCSV UTF-8 de hasta 20 MiB\n7 cabeceras y números finitos\nOpción de promedio por hora',INK)
    card('inference','contract',766,965,309,149,'Pipeline de inferencia',
         'StandardScaler original\nK-Means · centroide más cercano\nDistribución y perfiles del lote\nPCA de 2 componentes opcional',INK)
    card('delivery','contract',1091,965,351,149,'Respuesta y descargas',
         'JSON de resultados para Next.js\nOperaciones y resumen en CSV\nReporte en Markdown\nLotes sin persistencia en servidor',INK)

    legend_y = 1161
    line([(55,legend_y),(98,legend_y)],COPPER)
    label('key-train',109,legend_y-12,'Datos de entrenamiento',16,INK)
    line([(341,legend_y),(384,legend_y)],COPPER,True)
    label('key-model',395,legend_y-12,'Transferencia o carga de artefactos',16,INK)
    line([(710,legend_y),(753,legend_y)],BLUE)
    label('key-api',764,legend_y-12,'Solicitudes y resultados en producción',16,INK)
    for key, color, dashed, x in [('train',COPPER,False,55),('model',COPPER,True,341),('api',BLUE,False,710)]:
        cell = ET.SubElement(root,'mxCell',id='legend-'+key,edge='1',parent='1',
                             style=f'endArrow=block;endFill=1;strokeColor={color};strokeWidth=2.3;dashed={int(dashed)};dashPattern=7 5;')
        g = ET.SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})
        ET.SubElement(g,'mxPoint',x=str(x),y=str(legend_y),attrib={'as':'sourcePoint'})
        ET.SubElement(g,'mxPoint',x=str(x+43),y=str(legend_y),attrib={'as':'targetPoint'})
    ET.indent(file)
    ET.ElementTree(file).write(STEM.with_suffix('.drawio'),encoding='utf-8',xml_declaration=True)
    STEM.with_suffix('.svg').write_text('\n'.join([*svg,'</svg>']),encoding='utf-8')
    c.save()


if __name__ == '__main__':
    with TemporaryDirectory() as temp:
        pdf = Path(temp) / 'diagram.pdf'
        build(pdf)
        subprocess.run(['pdftoppm','-r','192','-png','-singlefile',str(pdf),str(STEM)],check=True)
