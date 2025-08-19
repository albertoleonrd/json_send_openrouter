import json
import requests
import os
import re
import sys
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

if not OPENROUTER_API_KEY:
    raise ValueError("La API key de OpenRouter no está configurada. Crea un archivo .env con OPENROUTER_API_KEY=tu_clave")

def create_prompt(word_data):
    prompt = f"""[<context> 
     <source_json> 
       {json.dumps(word_data, indent=2)} 
     </source_json> 
    <available_categories>Azione, Attività, Animale, Corpo, Abbigliamento, Colore, Comunicazione, Concetto, Connettore, Grado, Determinante, Direzione, Educazione, Emozione, Evento, Espressione, Famiglia, Cibo, Funzione, Grammatica, Salute, Modale, Modificatore, Musica, Natura, Numero, Oggetto, Persona, Luogo, Pianta, Pronome, Proprietà, Quantità, Relazione, Sport, Stato, Sostanza, Tecnologia, Tempo, Trasporto, Meteo, Lavoro</available_categories>
</context>
<role>Actuar como un lingüista y experto en la creación de material didáctico para estudiantes de italiano de nivel A1, cuya lengua nativa es el español. Tu especialidad es generar definiciones y ejemplos claros utilizando vocabulario controlado.</role>
<instructions>
    <analysis_procedure>
        1.  Analizar el objeto JSON proporcionado en <source_json>.
        2.  Identificar el valor del campo `term`.
        3.  Determinar la categoría gramatical (`part_of_speech`) del `term` en italiano.
        4.  Generar una definición (`definition`) clara y concisa en italiano para el `term`.
        5.  Clasificar el `term` en una de las <available_categories> basándose en su definición y uso.
        6.  Traducir el valor de `term` al español para generar el campo `term_es`.
        7.  Crear una oración simple en italiano para el campo `example` que cumpla estas condiciones:
            <case>
                <condition>La oración debe usar la palabra del campo `term`.</condition>
            </case>
            <case>
                <condition>El significado del `term` debe corresponder a la `definition` generada.</condition>
            </case>
            <case>
                <condition>El resto de palabras deben ser de vocabulario italiano de nivel A1.</condition>
            </case>
            <case>
                <condition>La estructura de la oración debe ser muy fácil de entender.</condition>
            </case>
        8.  Traducir la oración generada en `example` al español para crear `example_es`.
        9.  Construir un único objeto JSON que combine los campos originales y los nuevos generados.
    </analysis_procedure>
    <output_rules>
        <rule>Generar el resultado en un único bloque de código JSON.</rule>
        <rule>Incluir todos los campos del JSON original en la salida.</rule>
        <rule>Añadir los nuevos campos generados en el proceso.</rule>
        <rule>Sin agregar explicaciones fuera del bloque de código JSON.</rule>
        <rule>Sin usar markdown para el bloque de código.</rule>
    </output_rules>
</instructions>
<output_format> 
{{ 
    "id": "B9F4A05D",
    "term_source": "di",
    "rank": 1,
    "zipf_frequency": 7.59,
    "cefr_level": "A1",
    "part_of_speech": "preposizione",
    "definition": "Indica possesso, specificazione, origine o materiale.",
    "semantic_category": "Connettore",
    "term_target": "de",
    "example_source": "Il libro è di Maria.",
    "example_target": "El libro es de María."
}} 
</output_format>]"""
    return prompt

def send_to_openrouter(prompt):
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'model': 'google/gemini-2.5-flash-lite',
        'messages': [
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7,
        'max_tokens': 1000
    }
    response = requests.post(OPENROUTER_URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        print(f"Error en la solicitud: {response.status_code}")
        print(response.text)
        return None

def extract_json_from_response(response_text):
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                print("No se pudo encontrar un objeto JSON en la respuesta")
                return None
        except Exception as e:
            print(f"Error al extraer JSON: {e}")
            return None

def load_clean_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        content = re.sub(r'^json\[\[', '[', content)
        content = re.sub(r'\]\]$', ']', content)
        return json.loads(content)

def process_json_file(input_file):
    try:
        # Generar nombre de archivo de salida
        output_file = input_file.replace('.json', '_processed.json')
        if output_file == input_file:
            output_file = input_file.rsplit('.', 1)[0] + '_processed.json'
        
        word_data_list = load_clean_json(input_file)
        processed_data = []
        total_words = len(word_data_list)

        # Si existe archivo previo, cargarlo para continuar
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                try:
                    processed_data = json.load(f)
                except:
                    processed_data = []

        start_index = len(processed_data)

        for i in range(start_index, total_words):
            word_data = word_data_list[i]
            print(f"Procesando palabra {i+1}/{total_words}: {word_data.get('term', 'desconocido')}")
            prompt = create_prompt(word_data)
            response = send_to_openrouter(prompt)
            if response:
                processed_word = extract_json_from_response(response)
                if processed_word:
                    processed_data.append(processed_word)
                    print(f"  ✓ Procesado correctamente")
                else:
                    print(f"  ✗ Error al extraer JSON de la respuesta")
                    processed_data.append(word_data)
            else:
                print(f"  ✗ No se recibió respuesta de OpenRouter")
                processed_data.append(word_data)

            # Guardar progreso después de cada elemento
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)

        print(f"\nProcesamiento completado. Resultados guardados en {output_file}")
        return output_file

    except Exception as e:
        print(f"Error en el procesamiento: {e}")
        return None

def main():
    # Si se proporciona un argumento de línea de comandos, usarlo como archivo de entrada
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        if os.path.exists(input_file):
            process_json_file(input_file)
        else:
            print(f"El archivo {input_file} no existe.")
    else:
        print("Por favor, arrastra un archivo JSON sobre este script o proporciona la ruta como argumento.")

if __name__ == "__main__":
    main()
