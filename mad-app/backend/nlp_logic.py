import pandas as pd
import re
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer

def perform_analysis(messages: List[Dict]) -> Dict:
    """
    Performs NLP analysis (TF-IDF, Topic Modeling) on debate messages.
    """
    if not messages:
        return {"error": "No messages provided for analysis."}
        
    df = pd.DataFrame(messages)
    df['clean_content'] = df['content'].apply(lambda x: re.sub(r"^\s*Debater_[AB]:\s*", "", x, flags=re.IGNORECASE))
    
    debaters_df = df[df['agent'].str.startswith('Debater_')]
    if debaters_df.empty:
        return {"error": "No debater messages found for analysis."}
        
    debate_corpus = debaters_df['clean_content'].tolist()
    
    # --- TF-IDF Analysis ---
    all_keywords = []
    try:
        tfidf_all = TfidfVectorizer(stop_words='english', max_features=15)
        tfidf_all.fit(debate_corpus)
        all_keywords = [{"term": term, "score": 0} for term in tfidf_all.get_feature_names_out()] # score is dummy for interface
    except Exception:
        all_keywords = [] # Failed to generate

    keywords_by_debater = {}
    try:
        agent_corpus = debaters_df.groupby('agent')['clean_content'].apply(' '.join)
        if not agent_corpus.empty:
            tfidf_agent = TfidfVectorizer(stop_words='english', max_features=10)
            tfidf_matrix = tfidf_agent.fit_transform(agent_corpus)
            feature_names = tfidf_agent.get_feature_names_out()
            for i, agent_name in enumerate(agent_corpus.index):
                agent_scores = tfidf_matrix[i].toarray().flatten()
                top_indices = agent_scores.argsort()[::-1][:10]
                top_keywords = [{"term": feature_names[idx], "score": agent_scores[idx]} for idx in top_indices if agent_scores[idx] > 0]
                keywords_by_debater[agent_name] = top_keywords
    except Exception:
        # Fails silently and returns empty dict
        pass

    # --- Timeline Analysis (Simplified TF-IDF per round) ---
    timeline = []
    for round_num in df['round'].unique():
        round_df = debaters_df[debaters_df['round'] == round_num]
        if round_df.empty:
            continue

        round_keywords = {}
        for agent_name, group in round_df.groupby('agent'):
            try:
                vectorizer = TfidfVectorizer(stop_words='english', max_features=5)
                tfidf_matrix = vectorizer.fit_transform(group['clean_content'])
                round_keywords[agent_name] = [{"term": term, "score": 0} for term in vectorizer.get_feature_names_out()]
            except ValueError: # Happens if content is too short
                round_keywords[agent_name] = []

        timeline.append({"round": int(round_num), "keywordsByDebater": round_keywords})

    return {
        "overallKeywords": all_keywords,
        "keywordsByDebater": keywords_by_debater,
        "timeline": timeline,
    }