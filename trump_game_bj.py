import random
import discord

LOSE_COLOR = 0xE65245
WIN_COLOR = 0x009900
DRAW_COLOR = 0x696969
DEFAULT_COLOR = 0x87CEEB


class GameBlackJack:
    def __init__(self, player_id):
        self.player_id = player_id
        self.message_id = None
        self.deck = Deck()
        self.dealer = Dealer()
        self.player = Player()
        self.deck.shuffle()
        self.dealer.draw_card(self.deck)
        self.dealer.draw_card(self.deck)
        self.is_playing = False
        self.amount = 0
        # embedを作成
        self.embed = discord.Embed(
            title="BlackJack", description="Start Game", color=DEFAULT_COLOR
        )

    def start_game(self, amount):
        self.player.draw_card(self.deck)
        self.player.draw_card(self.deck)
        self.is_playing = True
        # embedのdiscriptionを更新
        self.embed.description = "----- Hit or Stand -----"
        # amountの不正値チェック
        if amount < 0:
            amount = 0
        self.amount = amount
        # embedにフィールドを追加
        self.embed.add_field(
            name="Dealer",
            value=self.dealer.get_cards_string(is_first=True),
            inline=False,
        )
        self.embed.add_field(
            name="Player", value=self.player.get_cards_string(), inline=False
        )
        # embedに掛け金のフィールドを追加。値は3桁ごとにカンマ区切り
        amount_string = "```fix\n" + "{:,}".format(self.amount) + "\n```"
        self.embed.add_field(name="Amount", value=amount_string, inline=False)

    async def react(self, reaction):
        if reaction.emoji.name == "🇭":
            await self.hit()
        elif reaction.emoji.name == "🇸":
            await self.stand()
        else:
            print("reaction error")
            return
        if not self.is_playing:
            await self.judge()

    async def hit(self):
        print("hit")
        self.player.draw_card(self.deck)
        if self.player.get_point() > 21:
            self.is_playing = False
            while self.dealer.get_point() < 17:
                self.dealer.draw_card(self.deck)
        # embedのフィールドを更新
        self.embed.set_field_at(
            1, name="Player", value=self.player.get_cards_string(), inline=False
        )

    async def stand(self):
        print("stand")
        self.is_playing = False
        while self.dealer.get_point() < 17:
            self.dealer.draw_card(self.deck)
        self.embed.set_field_at(
            1, name="Player", value=self.player.get_cards_string(), inline=False
        )

    async def judge(self):
        # embedのフィールドを更新
        self.embed.set_field_at(
            0, name="Dealer", value=self.dealer.get_cards_string(), inline=False
        )
        return_value = 0
        embed_color = DEFAULT_COLOR
        # どちらもバーストしていた場合
        if self.player.get_point() > 21 and self.dealer.get_point() > 21:
            self.embed.description = "--------- Draw ---------"
            return_value = self.amount
            # embedのカラーを黄に変更
            embed_color = DRAW_COLOR
        elif self.player.get_point() > 21:
            self.embed.description = "------- You Lose -------"
            # embedのカラーを赤に変更
            embed_color = LOSE_COLOR
        elif self.dealer.get_point() > 21:
            self.embed.description = "------- You Win -------"
            return_value = self.amount * 2
            # embedのカラーを青に変更
            embed_color = WIN_COLOR
        elif self.player.get_point() > self.dealer.get_point():
            self.embed.description = "------- You Win -------"
            return_value = self.amount * 2
            # embedのカラーを青に変更
            embed_color = WIN_COLOR
        elif self.player.get_point() < self.dealer.get_point():
            self.embed.description = "------- You Lose -------"
            # embedのカラーを赤に変更
            embed_color = LOSE_COLOR
        else:
            self.embed.description = "--------- Draw ---------"
            return_value = self.amount
            # embedのカラーを黄に変更
            embed_color = DRAW_COLOR
        # embedのカラーを更新
        self.embed.color = embed_color
        # embedに掛け金の変動値のフィールドを追加。値は3桁ごとにカンマ区切り
        change_string = "```fix\n" + "{:,}".format(return_value) + "\n```"
        self.embed.add_field(name="Change", value=change_string, inline=False)
        return return_value

    def set_message_id(self, message_id):
        self.message_id = message_id

    def get_message_id(self):
        return self.message_id

    def get_embed(self):
        return self.embed

    def get_is_playing(self):
        return self.is_playing

    def get_player_id(self):
        return self.player_id


class Deck:
    def __init__(self):
        self.cards = []
        for i in range(4):
            for j in range(1, 14):
                self.cards.append(Card(i, j))

    def shuffle(self):
        random.shuffle(self.cards)

    def draw_card(self):
        return self.cards.pop()


class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    def get_string(self):
        card_string = ""
        if self.suit == 0:
            card_string += "♠"
        elif self.suit == 1:
            card_string += "♥"
        elif self.suit == 2:
            card_string += "♦"
        elif self.suit == 3:
            card_string += "♣"

        if self.rank == 1:
            card_string += "A"
        elif self.rank == 11:
            card_string += "J"
        elif self.rank == 12:
            card_string += "Q"
        elif self.rank == 13:
            card_string += "K"
        else:
            card_string += str(self.rank)

        return card_string


class Dealer:
    def __init__(self):
        self.cards = []

    def draw_card(self, deck):
        self.cards.append(deck.draw_card())

    def get_cards_string(self, is_first=False):
        cards_string = "```txt\n"
        if is_first:
            cards_string += self.cards[0].get_string() + " *"
        else:
            for card in self.cards:
                cards_string += card.get_string() + " "
            cards_string += "\n[" + str(self.get_point()) + "]"
        cards_string += "\n```"
        return cards_string

    def get_point(self):
        point = 0
        one_count = 0
        for card in self.cards:
            if card.rank == 1:
                one_count += 1
                point += 11
            elif card.rank > 10:
                point += 10
            else:
                point += card.rank
        while point > 21 and one_count > 0:
            point -= 10
            one_count -= 1
        return point


class Player:
    def __init__(self):
        self.cards = []

    def draw_card(self, deck):
        self.cards.append(deck.draw_card())

    def get_cards_string(self):
        cards_string = "```txt\n"
        for card in self.cards:
            cards_string += card.get_string() + " "
        # カードの合計値を追加
        cards_string += "\n[" + str(self.get_point()) + "]\n```"
        return cards_string

    def get_point(self):
        point = 0
        one_count = 0
        for card in self.cards:
            if card.rank == 1:
                one_count += 1
                point += 11
            elif card.rank > 10:
                point += 10
            else:
                point += card.rank
        while point > 21 and one_count > 0:
            point -= 10
            one_count -= 1
        return point
