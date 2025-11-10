import json
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer # <-- IMPORTED CountVectorizer
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer



def run_analysis():
    # --- 1. Load Data from JSON ---
    try:
        with open('debate_history.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("Successfully loaded debate_history.json")
    except FileNotFoundError:
        print("Error: 'debate_history.json' not found.")
        print("Please make sure the JSON file is in the same directory as this script.")
        return
    except json.JSONDecodeError:
        print("Error: 'debate_history.json' is not a valid JSON file.")
        return

    # Load messages into a DataFrame
    df = pd.DataFrame(data['messages'])

    # Prepare a "clean" text column for NLP
    df['clean_content'] = df['content'].apply(lambda x: re.sub(r"^\s*Debater_[AB]:\s*", "", x, flags=re.IGNORECASE))

    # Create the corpus of just the debaters' arguments
    debate_corpus = df[df['agent'] != 'Judge']['clean_content']
    debate_documents = debate_corpus.tolist()

    if not debate_documents:
        print("Error: No debate messages found (exluding the Judge). Cannot run analysis.")
        return

    # --- 2. TF-IDF Keyword Extraction (Whole Debate) ---
    print("\n" + "="*50)
    print("   TF-IDF Keywords: Entire Debate")
    print("="*50)

    try:
        tfidf_all = TfidfVectorizer(stop_words='english', max_features=15)
        tfidf_all.fit(debate_corpus)
        all_keywords = tfidf_all.get_feature_names_out()
        print("Top 15 keywords for the entire debate:")
        print(", ".join(all_keywords))

    except Exception as e:
        print(f"Error during whole-debate TF-IDF: {e}")


    # --- 3. TF-IDF Keyword Extraction (Per Debater) ---
    print("\n" + "="*50)
    print("   TF-IDF Keywords: Per Debater")
    print("="*50)

    try:
        # We only want to compare the debaters
        agent_corpus = df[df['agent'].isin(['Debater_A', 'Debater_B'])].groupby('agent')['clean_content'].apply(' '.join)
        
        if agent_corpus.empty:
            print("No content found for Debater_A or Debater_B.")
        else:
            tfidf_agent = TfidfVectorizer(stop_words='english', max_features=10)
            tfidf_matrix = tfidf_agent.fit_transform(agent_corpus)
            feature_names = tfidf_agent.get_feature_names_out()

            for i, agent_name in enumerate(agent_corpus.index):
                agent_scores = tfidf_matrix[i].toarray().flatten()
                top_indices = agent_scores.argsort()[::-1][:10]
                top_keywords = [feature_names[idx] for idx in top_indices if agent_scores[idx] > 0]
                
                print(f"\nTop 10 keywords for {agent_name}:")
                print(", ".join(top_keywords))
    
    except Exception as e:
        print(f"Error during per-debater TF-IDF: {e}")


    # --- 4. BERTopic Topic Modeling (Whole Debate) ---
    print("\n" + "="*50)
    print("   BERTopic: Topic Modeling")
    print("="*50)
    
    try:
        embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        
        min_topic_size = 2 
        
        vectorizer_model = CountVectorizer(stop_words="english") 
        
        print(f"Running BERTopic with min_topic_size={min_topic_size} and stop-word removal...")
        
        topic_model = BERTopic(
            embedding_model=embedding_model,
            min_topic_size=min_topic_size,
            vectorizer_model=vectorizer_model, 
            verbose=True
        )
        
        topics, probabilities = topic_model.fit_transform(debate_documents)
        
        print("\nBERTopic analysis complete.")
        
        print("\nTopics found (Topic -1 = Outliers):")
        print(topic_model.get_topic_info())
        
        print("\nKeywords for each main topic:")
        for topic_id in topic_model.get_topics().keys():
            if topic_id == -1:
                continue 
            
            topic_words = [word for word, score in topic_model.get_topic(topic_id)][:7]
            print(f"Topic {topic_id}:", ", ".join(topic_words))

    except ImportError:
        print("\nError: BERTopic or SentenceTransformers not found.")
        print("Please run: pip install bertopic sentence-transformers")
    except Exception as e:
        print(f"An error occurred during BERTopic analysis: {e}")


# --- Run the main function ---
if __name__ == "__main__":
    run_analysis()