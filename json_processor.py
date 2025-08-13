import json
import requests
import os
from dotenv import load_dotenv

# Cargar variables de entorno (para la API key de OpenRouter)
load_dotenv()

# Configuración
INPUT_FILE = 'worddata_a1.json'
OUTPUT_FILE = 'worddata_a1_processed.json'
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

# Verificar que la API key esté disponible
if not OPENROUTER_API_KEY:
    raise ValueError("La API key de OpenRouter no está configurada. Crea un archivo .env con OPENROUTER_API_KEY=tu_clave")

# Función para crear el prompt con el formato especificado
def create_prompt(word_data):
    prompt = f"""[<context> 
     <source_json> 
       {json.dumps(word_data, indent=2)} 
     </source_json> 
 </context> 
 <role>Actuar como un experto en la creación de material didáctico para estudiantes de inglés de nivel A1. Tu especialidad es generar ejemplos claros y sencillos utilizando un vocabulario estrictamente controlado.</role> 
 <instructions> 
     <analysis_procedure> 
         1. Analizar el JSON proporcionado en <source_json>. 
         2. Identificar el valor de los campos `term` y `definition`. 
         3. Traducir el valor de `term` al español para generar el campo `term_es`. 
         4. Crear una oración simple para el campo `example` que cumpla estas condiciones: 
             a. La oración debe usar la palabra del campo `term`. 
             b. El significado del `term` en la oración debe corresponder al del campo `definition`. 
             c. Todas las demás palabras usadas deben pertenecer al nivel A1 del vocabulario Oxford 3000. 
             d. La estructura de la oración debe ser fácil de entender para un estudiante de nivel A1. 
         5. Añadir el campo `example_es` al JSON final. 
         6. Traducir la oración generada en `example` al español para crear `example_es`. 
         7. Construir un objeto JSON final que combine los campos originales y los nuevos. 
     </analysis_procedure> 
     <output_rules> 
         <rule>Generar el resultado en un único bloque de código JSON.</rule> 
         <rule>Incluir todos los campos del JSON original en la salida.</rule> 
         <rule>Añadir los nuevos campos: `term_es`, `example`, `example_es`.</rule> 
         <rule>Sin agregar explicaciones o texto fuera del bloque de código JSON.</rule> 
         <rule>Sin usar markdown para el bloque de código.</rule> 
     </output_rules> 
 </instructions> 
 <output_format> 
   { 
     "id": "...", 
     "term": "...", 
     "pronunciation": "...", 
     "part_of_speech": "...", 
     "level": "...", 
     "definition": "...", 
     "term_es": "...", 
     "example": "...", 
     "example_es": "..." 
   } 
 </output_format>]"""
    return prompt

# Función para enviar el prompt a OpenRouter y obtener la respuesta
def send_to_openrouter(prompt):
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'google/gemini-2.5-flash',  # Puedes cambiar el modelo según tus necesidades
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

# Función para extraer el JSON de la respuesta
def extract_json_from_response(response_text):
    try:
        # Intentar analizar directamente la respuesta como JSON
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Si falla, intentar extraer el bloque JSON de la respuesta
        try:
            # Buscar el JSON en la respuesta (puede estar en un bloque de código)
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                print("No se pudo encontrar un objeto JSON en la respuesta")
                return None
        except Exception as e:
            print(f"Error al extraer JSON: {e}")
            return None

# Función principal
def main():
    try:
        # Leer el archivo JSON de entrada
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            word_data_list = json.load(f)
        
        processed_data = []
        total_words = len(word_data_list)
        
        # Procesar cada palabra
        for i, word_data in enumerate(word_data_list):
            print(f"Procesando palabra {i+1}/{total_words}: {word_data.get('term', 'desconocido')}")
            
            # Crear el prompt y enviarlo a OpenRouter
            prompt = create_prompt(word_data)
            response = send_to_openrouter(prompt)
            
            if response:
                # Extraer el JSON de la respuesta
                processed_word = extract_json_from_response(response)
                if processed_word:
                    processed_data.append(processed_word)
                    print(f"  ✓ Procesado correctamente")
                else:
                    print(f"  ✗ Error al extraer JSON de la respuesta")
                    # Si hay error, guardar la palabra original
                    processed_data.append(word_data)
            else:
                print(f"  ✗ No se recibió respuesta de OpenRouter")
                # Si hay error, guardar la palabra original
                processed_data.append(word_data)
        
        # Guardar los resultados en un archivo JSON
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)
        
        print(f"\nProcesamiento completado. Resultados guardados en {OUTPUT_FILE}")
    
    except Exception as e:
        print(f"Error en el procesamiento: {e}")

if __name__ == "__main__":
    main()