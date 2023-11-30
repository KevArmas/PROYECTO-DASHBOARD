import pandas as pd
from bokeh.plotting import figure, show
from bokeh.layouts import row, column
from bokeh.models import ColumnDataSource, RangeSlider, CustomJS
from bokeh.transform import cumsum
from bokeh.palettes import Category10
import mysql.connector
from math import pi

# Función para cargar datos desde MySQL
def load_data_from_mysql():
    connection = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="clinicalpaper"
    )
    cursor = connection.cursor()

    # Consulta SQL para obtener datos de patientinfo y tumorcharacteristics
    query = """
        SELECT p.PatientID, p.`Date of Birth (Days)`, p.`Race and Ethnicity`, p.`Days to death (from the date of diagnosis)`,
                t.ER, t.PR, t.HER2
        FROM patientinfo p
        JOIN tumorcharacteristics t ON p.PatientID = t.PatientID
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    connection.close()

    # Crear DataFrame con los resultados
    df = pd.DataFrame(results, columns=["PatientID", "Date of Birth (Days)", "Race and Ethnicity", "Days to death (from the date of diagnosis)",
                                        "ER", "PR", "HER2"])
    df["Age"] = abs(df["Date of Birth (Days)"]) // 365

    # Crear columnas 'Murio ER', 'Murio PR' y 'Murio HER2'
    df['Murio ER'] = df.apply(lambda row: '1' if row['Days to death (from the date of diagnosis)'] != 'NP' and row['ER'] == 1
                                else '2' if row['Days to death (from the date of diagnosis)'] != 'NP' and row['ER'] == 0
                                else '4' if row['Days to death (from the date of diagnosis)'] == 'NP' and row['ER'] == 1
                                else '3', axis=1)
    df['Murio PR'] = df.apply(lambda row: '1' if row['Days to death (from the date of diagnosis)'] != 'NP' and row['PR'] == 1
                                else '2' if row['Days to death (from the date of diagnosis)'] != 'NP' and row['PR'] == 0
                                else '4' if row['Days to death (from the date of diagnosis)'] == 'NP' and row['PR'] == 1
                                else '3', axis=1)
    df['Murio HER2'] = df.apply(lambda row: '1' if row['Days to death (from the date of diagnosis)'] != 'NP' and row['HER2'] == 1
                                else '2' if row['Days to death (from the date of diagnosis)'] != 'NP' and row['HER2'] == 0
                                else '4' if row['Days to death (from the date of diagnosis)'] == 'NP' and row['HER2'] == 1
                                else '3', axis=1)

    df.to_csv('Edad.csv', index=False)

    return df

# Función para actualizar el gráfico de líneas basado en el rango de edad seleccionado
def update_line_chart(attr, old_range, new_range):
    age_min, age_max = new_range[0], new_range[1]

    # Filtrar datos basados en la edad
    filtered_data = df['Age'][(df['Age'] >= age_min) & (df['Age'] <= age_max)]

    # Calcular nueva línea
    x_new = list(range(age_min, age_max + 1))
    y_new = [filtered_data[filtered_data == age].count() for age in x_new]

    # Actualizar el origen de datos de la línea
    line_source.data['x'] = x_new
    line_source.data['y'] = y_new

# Cargar datos desde MySQL
df = load_data_from_mysql()

# Crear el gráfico de líneas utilizando Bokeh
p = figure(height=400, width=800, title="Distribución de Edades de Pacientes con Cáncer", toolbar_location=None, tools="")

# Calcular los datos de la línea
x = df['Age'].value_counts().sort_index().index
y = df['Age'].value_counts().sort_index().values

# Crear el origen de datos de la línea
line_source = ColumnDataSource(data=dict(x=x, y=y))
p.line('x', 'y', source=line_source, line_color="green", line_width=2)

# Añadir nombres a los ejes y título del gráfico
p.xaxis.axis_label = "Edad"
p.yaxis.axis_label = "Frecuencia"
p.title.text_font_size = "16px"

# Crear un rango slider para filtrar por edad
age_slider = RangeSlider(start=df['Age'].min(), end=df['Age'].max(), value=(df['Age'].min(), df['Age'].max()), step=1, title="Filtrar por Edad")

# Definir la función de actualización de datos para el gráfico de líneas
update_data = CustomJS(args=dict(source=line_source, df=ColumnDataSource(df), age_slider=age_slider),
                        code="""
                            const data = df.data;
                            const age_min = age_slider.value[0];
                            const age_max = age_slider.value[1];

                            // Filtrar datos basados en la edad
                            const filtered_data = data['Age'].filter(function (age) {
                                return age >= age_min && age <= age_max;
                            });

                            // Calcular nueva línea
                            const x_new = Array.from({length: age_max - age_min + 1}, (_, i) => age_min + i);
                            const y_new = Array.from({length: age_max - age_min + 1}, () => 0);

                            for (let i = 0; i < filtered_data.length; i++) {
                                const index = filtered_data[i] - age_min;
                                y_new[index]++;
                            }

                            // Actualizar el origen de datos de la línea
                            source.data['x'] = x_new;
                            source.data['y'] = y_new;
                            source.change.emit();
                        """
                        )

# Asignar la función de actualización al evento 'value' del rango slider
age_slider.js_on_change('value', update_data)

# Crear un layout con el gráfico de líneas y el rango slider
layout_line = column(p, age_slider)

# Crear el gráfico de pastel
categorias = ["white", "black", "asian", "native", "hispanic", "multi", "hawa", "amer indian", "NA"]
conteos = df['Race and Ethnicity'].value_counts()

data_pie = pd.DataFrame({'Categorias': conteos.index, 'Value': conteos.values})
data_pie['angle'] = data_pie['Value'] / data_pie['Value'].sum() * 2 * pi
data_pie['color'] = Category10[len(categorias)]

# Mapear números a etiquetas
etiquetas_categoria = {1: "White", 2: "Black", 3: "Asian", 4: "Native", 5: "Hispanic", 6: "Multi", 7: "Hawa", 8: "Amer Indian", 9: "NA"}
data_pie['Categorias'] = data_pie['Categorias'].map(etiquetas_categoria)

# Crear el gráfico de pastel
p_pie = figure(height=400, width=600, title="Distribución Étnica de Pacientes", toolbar_location=None,
                tools="hover", tooltips="@Categorias: @Value", x_range=(-1, 1))

wedge = p_pie.wedge(x=0, y=0, radius=0.4, 
                    start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
                    line_color="white", fill_color='color', legend_field='Categorias', source=data_pie)

# Añadir leyenda
p_pie.legend.label_text_font_size = "10pt"

p_pie.axis.axis_label = None
p_pie.axis.visible = False
p_pie.grid.grid_line_color = None

# Crear un layout con el gráfico de pastel
layout_pie = column(p_pie)

# Conteo de valores únicos en las columnas 'Murio ER', 'Murio PR' y 'Murio HER2'
murio_er_counts = df['Murio ER'].value_counts()
murio_pr_counts = df['Murio PR'].value_counts()
murio_her2_counts = df['Murio HER2'].value_counts()

# Convertir el índice a una lista de cadenas
x_values_er = list(map(str, murio_er_counts.index))
x_values_pr = list(map(str, murio_pr_counts.index))
x_values_her2 = list(map(str, murio_her2_counts.index))

# Configurar la fuente de datos para Bokeh
color_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
source_er = ColumnDataSource(data=dict(x=x_values_er, y=murio_er_counts.values, color=color_palette[:len(x_values_er)]))
source_pr = ColumnDataSource(data=dict(x=x_values_pr, y=murio_pr_counts.values, color=color_palette[:len(x_values_pr)]))
source_her2 = ColumnDataSource(data=dict(x=x_values_her2, y=murio_her2_counts.values, color=color_palette[:len(x_values_her2)]))

# Crear la figura interactiva para 'Murio ER'
p_er = figure(x_range=x_values_er, title='Tumor Characteristics "ER"', toolbar_location=None, tools='', height=350)
p_er.vbar(x='x', top='y', width=0.9, source=source_er, line_color="white", fill_color='color')

# Crear la figura interactiva para 'Murio PR'
p_pr = figure(x_range=x_values_pr, title='Tumor Characteristics "PR"', toolbar_location=None, tools='', height=350)
p_pr.vbar(x='x', top='y', width=0.9, source=source_pr, line_color="white", fill_color='color')

# Crear la figura interactiva para 'Murio HER2'
p_her2 = figure(x_range=x_values_her2, title='Tumor Characteristics "HER2"', toolbar_location=None, tools='', height=350)
p_her2.vbar(x='x', top='y', width=0.9, source=source_her2, line_color="white", fill_color='color')

# Mostrar las figuras interactivas
show(row(column(layout_line), column(p_er, p_pr, p_her2), layout_pie))