import requests

BASE_URL = "http://localhost:8000"


def get_token(email: str, password: str) -> str:
    """
    Get an access token for the given user.
    If the user does not exist, try to register first.
    """
    # Try login first
    data = {"username": email, "password": password}
    resp = requests.post(f"{BASE_URL}/token", data=data)

    if resp.status_code == 401:
        # Try to register the user, then login again
        print("User not found, registering a new user...")
        reg_payload = {
            "email": email,
            "password": password,
            "full_name": "Seed User",
        }
        reg_resp = requests.post(f"{BASE_URL}/register", json=reg_payload)
        reg_resp.raise_for_status()

        resp = requests.post(f"{BASE_URL}/token", data=data)

    resp.raise_for_status()
    return resp.json()["access_token"]


def seed_papers(token: str):
    """
    Create a bunch of demo papers via the /papers endpoint.
    Backend must be running on BASE_URL.
    """
    headers = {"Authorization": f"Bearer {token}"}

    demo_papers = [
        {
            "title": "Deep Learning for Natural Language Processing",
            "authors": "Palash Goyal,  Sumit Pandey",
            "abstract": "In this chapter, we survey various deep learning techniques that are applied in the field of Natural Language Processing. We also propose methods for computing sentence embedding and document embedding. Both sentence embedding and document embedding are able to capture the distribution of hidden concepts in the corresponding sentence or document. The document embedding also provides a way to present and process documents as images. ",
            "tags": "machine learning, nlp, deep learning",
            "doi": "10.1007/978-1-4842-3685-7",
        },
        {
            "title": "Attention Is All You Need",
            "authors": "Ashish Vaswani, Noam Shazeer, Niki Parmar",
            "abstract": "We propose the Transformer, a new architecture for handling sequential data without recurrence or convolution.",
            "tags": "transformers, nlp, deep learning",
            "doi": "10.48550/arXiv.1706.03762",
        },
        {
            "title": "A Survey on Graph Neural Networks",
            "authors": "Zonghan Wu, Shirui Pan",
            "abstract": "This paper surveys recent advances in graph neural networks for representation learning on graphs.",
            "tags": "graph neural networks, gnn, machine learning",
            "doi": "10.1109/TPAMI.2020.2978386",
        },
        {
            "title": "The Elements of Statistical Learning",
            "authors": "Trevor Hastie, Robert Tibshirani, Jerome Friedman",
            "abstract": "Comprehensive coverage of statistical learning techniques including regression, classification, and unsupervised learning.",
            "tags": "statistics, machine learning, theory",
            "doi": "10.1007/978-0-387-84858-7",
        },
        {
            "title": "ImageNet Classification with Deep Convolutional Neural Networks",
            "authors": "Alex Krizhevsky, Ilya Sutskever, Geoffrey Hinton",
            "abstract": "We demonstrate that a deep convolutional neural network can achieve state-of-the-art results on the ImageNet dataset.",
            "tags": "computer vision, cnn, image classification",
            "doi": "10.1145/3065386",
        },
        {
            "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            "authors": "Jacob Devlin, Ming-Wei Chang",
            "abstract": "BERT introduces a new language representation model that is pre-trained on large text corpora and fine-tuned for downstream tasks.",
            "tags": "bert, transformers, nlp",
            "doi": "10.48550/arXiv.1810.04805",
        },
        {
            "title": "AutoML: A Survey of the State-of-the-Art",
            "authors": "Frank Hutter, Lars Kotthoff, Joaquin Vanschoren",
            "abstract": "Survey of automated machine learning techniques, including hyperparameter optimization and neural architecture search.",
            "tags": "automl, hyperparameter optimization, machine learning",
            "doi": "10.1007/978-3-030-05318-5_1",
        },
        {
            "title": "An Introduction to Recommendation Systems",
            "authors": "Jannach Dietmar",
            "abstract": "Overview of collaborative filtering, content-based, and hybrid recommendation methods with practical applications.",
            "tags": "recommender systems, collaborative filtering, content-based",
            "doi": "10.1016/B978-0-12-415781-1.00001-9",
        },
        {
            "title": "XGBoost: A Scalable Tree Boosting System",
            "authors": "Tianqi Chen, Carlos Guestrin",
            "abstract": "We introduce XGBoost, a scalable and efficient gradient boosting library widely used in machine learning competitions.",
            "tags": "xgboost, gradient boosting, machine learning",
            "doi": "10.1145/2939672.2939785",
        },
        {
            "title": "Generative Adversarial Networks",
            "authors": "Ian Goodfellow, Jean Pouget-Abadie",
            "abstract": "GANs are a class of generative models that use a game-theoretic framework to generate realistic data.",
            "tags": "gan, generative models, deep learning",
            "doi": "10.1145/3422622",
        },
    ]

    for i, paper in enumerate(demo_papers, start=1):
        files = {}  # No PDF for now; this uses metadata only
        data = {
            "title": paper["title"],
            "authors": paper["authors"],
            "abstract": paper["abstract"],
            "tags": paper["tags"],
            "doi": paper.get("doi", ""),
        }
        resp = requests.post(f"{BASE_URL}/papers", headers=headers, data=data, files=files)
        try:
            resp.raise_for_status()
        except Exception as e:
            print(f"[{i}] Failed to create paper '{paper['title']}': {e} - {resp.text}")
        else:
            print(f"[{i}] Created paper: {paper['title']}")


def main():
    print("=== Paper Seeder ===")
    print("Backend must be running at", BASE_URL)
    email = input("Enter email to use for seeding (will be created if needed): ").strip()
    password = input("Enter password to use: ").strip()

    token = get_token(email, password)
    print("Got access token. Seeding demo papers...")
    seed_papers(token)
    print("Done. You can now see these papers in the frontend and get recommendations.")


if __name__ == "__main__":
    main()


