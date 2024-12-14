from flask import Flask, request, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pokepoke.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# モデル定義
class Deck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    my_deck_id = db.Column(db.Integer, db.ForeignKey('deck.id'), nullable=False)
    opponent_deck_id = db.Column(db.Integer, db.ForeignKey('deck.id'), nullable=False)
    result = db.Column(db.String(10), nullable=False)  # 'win', 'lose'
    date = db.Column(db.DateTime, nullable=False)

# 初回起動時にデータベースを作成
with app.app_context():
    db.create_all()

# ルート
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register_deck', methods=['GET', 'POST'])
def register_deck():
    message = None  # 成功メッセージ用の変数
    if request.method == 'POST':
        deck_name = request.form['deck_name']
        if deck_name:
            new_deck = Deck(name=deck_name)
            db.session.add(new_deck)
            db.session.commit()
            message = f"Deck '{deck_name}' registered successfully!"  # 成功メッセージをセット
    return render_template('register_deck.html', message=message)


@app.route('/record_match', methods=['GET', 'POST'])
def record_match():
    message = None  # 成功メッセージ用の変数
    if request.method == 'POST':
        my_deck_id = request.form['my_deck_id']
        opponent_deck_id = request.form['opponent_deck_id']
        result = request.form['result']
        if my_deck_id and opponent_deck_id and result:
            japan_time = datetime.now(pytz.timezone('Asia/Tokyo'))
            match = Match(
                my_deck_id=my_deck_id,
                opponent_deck_id=opponent_deck_id,
                result=result,
                date=japan_time.date()
            )
            db.session.add(match)
            db.session.commit()
            message = "Match recorded successfully!"  # 成功メッセージをセット
    decks = Deck.query.all()
    return render_template('record_match.html', decks=decks, message=message)


@app.route('/stats/<int:deck_id>')
def stats(deck_id):
    # 指定されたデッキを取得
    deck = Deck.query.get(deck_id)
    if not deck:
        return "Deck not found.", 404

    # 全体の勝率を計算
    total_matches = Match.query.filter_by(my_deck_id=deck_id).count()
    wins = Match.query.filter_by(my_deck_id=deck_id, result='win').count()
    if total_matches > 0:
        overall_win_rate = (wins / total_matches) * 100
    else:
        overall_win_rate = 0

    # 各対戦相手に対する勝敗数と勝率を計算
    my_deck = db.aliased(Deck)
    opponent_deck = db.aliased(Deck)

    opponent_stats = db.session.query(
        opponent_deck.name.label('opponent_name'),
        db.func.count(Match.id).label('total_matches'),
        db.func.sum(db.case((Match.result == 'win', 1), else_=0)).label('wins')
    ).join(opponent_deck, Match.opponent_deck_id == opponent_deck.id)\
     .filter(Match.my_deck_id == deck_id)\
     .group_by(opponent_deck.name).all()

    stats = []
    for opponent in opponent_stats:
        win_rate = (opponent.wins / opponent.total_matches) * 100 if opponent.total_matches > 0 else 0
        stats.append({
            'opponent_name': opponent.opponent_name,
            'total_matches': opponent.total_matches,
            'wins': opponent.wins,
            'win_rate': win_rate
        })

    return render_template(
        'stats.html',
        deck_name=deck.name,
        overall_win_rate=overall_win_rate,
        total_matches=total_matches,
        stats=stats
    )



@app.route('/select_deck', methods=['GET', 'POST'])
def select_deck():
    if request.method == 'POST':
        deck_id = request.form['deck_id']
        return redirect(f'/stats/{deck_id}')
    decks = Deck.query.all()  # 登録されたすべてのデッキを取得
    return render_template('select_deck.html', decks=decks)

@app.route('/match_history', methods=['GET', 'POST'])
def match_history():
    if request.method == 'POST':
        match_id = request.form.get('match_id')
        if match_id:
            match = Match.query.get(match_id)
            if match:
                db.session.delete(match)
                db.session.commit()

    # デッキテーブルのエイリアス
    my_deck = db.aliased(Deck)
    opponent_deck = db.aliased(Deck)

    # 全対戦履歴を取得
    matches = db.session.query(
        Match.id, Match.date,
        my_deck.name.label('my_deck_name'),
        opponent_deck.name.label('opponent_deck_name'),
        Match.result
    ).join(my_deck, my_deck.id == Match.my_deck_id)\
     .join(opponent_deck, opponent_deck.id == Match.opponent_deck_id)\
     .all()

    # 日付をフォーマット（例: YYYY-MM-DD）
    formatted_matches = [
        {
            'id': match.id,
            'date': match.date.strftime('%Y-%m-%d'),  # 日付をフォーマット
            'my_deck_name': match.my_deck_name,
            'opponent_deck_name': match.opponent_deck_name,
            'result': match.result
        }
        for match in matches
    ]

    return render_template('match_history.html', matches=formatted_matches)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)