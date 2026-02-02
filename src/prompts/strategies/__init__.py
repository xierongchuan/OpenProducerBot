from src.prompts.strategies.scalp import ScalpStrategy
from src.prompts.strategies.intraday import IntradayStrategy
from src.prompts.strategies.swing import SwingStrategy

STRATEGIES = {
    "SCALP": ScalpStrategy,
    "INTRADAY": IntradayStrategy,
    "SWING": SwingStrategy,
}
