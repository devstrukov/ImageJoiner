from app import app as flask_app


def _get_session_captcha(client):
    with client.session_transaction() as session:
        return session.get("captcha_answer")


def test_index_contains_required_form_inputs(tmp_path):
    flask_app.config["TESTING"] = True
    flask_app.config["UPLOAD_FOLDER"] = str(tmp_path)

    client = flask_app.test_client()
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="captcha_answer"' in html
    assert 'id="captchaAnswer"' in html
    assert 'name="image1"' in html
    assert 'name="image2"' in html
    assert 'name="orientation"' in html
    assert 'value="vertical"' in html
    assert 'value="horizontal"' in html


def test_results_captcha_validation(tmp_path):
    flask_app.config["TESTING"] = True
    flask_app.config["UPLOAD_FOLDER"] = str(tmp_path)

    client = flask_app.test_client()

    # GET / initializes captcha in session.
    client.get("/")
    expected_answer = _get_session_captcha(client)
    assert expected_answer is not None

    wrong_response = client.post(
        "/results",
        data={"captcha_answer": str(expected_answer + 1)},
        follow_redirects=True,
    )
    wrong_html = wrong_response.get_data(as_text=True)
    assert wrong_response.status_code == 200
    assert "Неверный ответ в поле проверки" in wrong_html

    # Refresh captcha for a clean successful captcha check.
    client.get("/")
    expected_answer = _get_session_captcha(client)
    ok_response = client.post(
        "/results",
        data={"captcha_answer": str(expected_answer)},
        follow_redirects=True,
    )
    ok_html = ok_response.get_data(as_text=True)
    assert ok_response.status_code == 200
    # If captcha is correct, request reaches next validation stage (files check).
    assert "Нужно загрузить оба изображения." in ok_html
