from sqlalchemy.orm import Session
from sqlalchemy import text
import google.generativeai as genai
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from ..core.config import settings

# Configuração das ferramentas de IA
try:
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
except Exception as e:
    print(f"Erro ao inicializar serviços de IA: {e}")
    pinecone_index = None

# Carregamento do modelo local de embeddings
try:
    embedder = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
except Exception as e:
    print(f"Erro ao carregar modelo embeddings: {e}")
    embedder = None


def sincronizar_base_conhecimento(db: Session):
    if pinecone_index is None:
        print("Serviço Pinecone não inicializado. Sincronização abortada.")
        return
        
    try:
        print("Iniciando a sincronização da base de conhecimento...")
        
        # Consulta as informações do Postgress referente ao profissional
        query = text("""
        SELECT 
            p.codprofissional, 
            p.nome AS nome_profissional,
            p.especialidade, 
            p.crm,
            c.nome_fantasia AS nome_clinica,
            gh.dia, 
            gh.horainciomanha, 
            gh.horafimmanha, 
            gh.horainciotarde, 
            gh.horafimtarde,
            tc.nome AS nome_consulta, 
            vc.valor
        FROM profissionais p
        LEFT JOIN profissionais_clinicas pc ON p.codprofissional = pc.codprofissional
        LEFT JOIN clinicas c ON pc.codclinica = c.codclinica
        LEFT JOIN grade_horarios gh ON p.codprofissional = gh.codprofissional
        LEFT JOIN valores_consulta vc ON p.codprofissional = vc.codprofissional
        LEFT JOIN tipos_consulta tc ON vc.codtipoconsulta = tc.codtipoconsulta
        WHERE p.situacao = 'Ativo';
        """)
        
        results = db.execute(query).mappings().all()
        
        if not results:
            print("Nenhum dado de profissional encontrado para sincronizar.")
            return

        # Estrutura para agrupar todos os fatos por profissional
        fatos_por_profissional = {}

        for row in results:
            prof_id = row['codprofissional']
            if prof_id not in fatos_por_profissional:
                fatos_por_profissional[prof_id] = {
                    "info_basica": f"O profissional {row['nome_profissional']}, especialista em {row['especialidade']}, possui o CRM {row['crm']}.",
                    "clinicas": set(),
                    "horarios": set(),
                    "valores": set()
                }
            
            if row['nome_clinica']:
                fatos_por_profissional[prof_id]["clinicas"].add(f"{row['nome_profissional']} atende na {row['nome_clinica']}.")
            
            if row['dia']:
                horario_str = f"Na {row['dia']}, {row['nome_profissional']} trabalha de {row['horainciomanha']} às {row['horafimmanha']} e de {row['horainciotarde']} às {row['horafimtarde']}."
                fatos_por_profissional[prof_id]["horarios"].add(horario_str)

            if row['nome_consulta'] and row['valor']:
                valor_str = f"Para a consulta do tipo '{row['nome_consulta']}', o valor cobrado por {row['nome_profissional']} é de R$ {row['valor']}."
                fatos_por_profissional[prof_id]["valores"].add(valor_str)

        # Junta todos os fatos em uma lista final para embedding
        fatos_finais = []
        for prof_id, data in fatos_por_profissional.items():
            fatos_finais.append(data["info_basica"])
            fatos_finais.extend(list(data["clinicas"]))
            fatos_finais.extend(list(data["horarios"]))
            fatos_finais.extend(list(data["valores"]))
        
        # Remove duplicatas, caso existam
        fatos_finais = list(set(fatos_finais))

        print(f"Total de {len(fatos_finais)} fatos gerados para indexação.")

        # Gera embeddings localmente
        embedding_result = embedder.encode(fatos_finais, convert_to_numpy=True)

        # # Gera os embeddings em lote com o Gemini
        # embedding_result = genai.embed_content(model="models/embedding-001", content=fatos_finais)
        
        vetores_para_salvar = []
        for i, texto in enumerate(fatos_finais):
            # Cria um ID único para cada fato baseado no seu conteúdo
            vetor_id = f"fato_{hash(texto)}"
            vetores_para_salvar.append({
                "id": vetor_id,
                "values": embedding_result[i].tolist(),
                "metadata": {"texto": texto}
            })

        if vetores_para_salvar:
            # Apaga os dados antigos
            try:
                pinecone_index.delete(delete_all=True, namespace="")
            except Exception as e:
                print(f"Aviso: não foi possível limpar namespace (pode não existir ainda): {e}")
            
            # Insere os novos dados
            pinecone_index.upsert(vectors=vetores_para_salvar, namespace="")
            print(f"Sincronização concluída: {len(vetores_para_salvar)} fatos indexados no Pinecone.")

    except Exception as e:
        print(f"Ocorreu um erro durante a sincronização: {e}")