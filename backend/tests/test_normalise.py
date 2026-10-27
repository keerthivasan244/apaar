from app.services.normalise import hash_phone, normalise_name


def test_mohammed_variants_equal():
    assert normalise_name("Mohd Aslam") == normalise_name("Muhammad Aslam") == "mohammed aslam"
    assert normalise_name("MD. Aslam") == "mohammed aslam"


def test_honorifics_and_punctuation_stripped():
    assert normalise_name("Dr. Shri  Ravi   Kumar") == "ravi kumar"
    assert normalise_name("Smt. Lakshmi") == "lakshmi"


def test_repeated_vowels_collapsed():
    assert normalise_name("Snehaa") == "sneha"
    assert normalise_name("Deepa") == normalise_name("Dipa".replace("i", "ee"))
    assert normalise_name("Kumaar Singh") == "kumar singh"
    assert normalise_name("Harpreet Sing") == "harpret singh"


def test_phone_hash():
    h1, last4 = hash_phone("+91 98765-43210")
    h2, _ = hash_phone("9876543210")
    assert h1 == h2 and last4 == "3210"
    assert hash_phone("12345") == (None, None)
    assert hash_phone(None) == (None, None)
