from random import choice
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("weather")


@mcp.tool()
def get_weather(city: str) -> str:
    """
    Returns weather of the city
    :param city: The city to get the weather for
    """
    adj = choice([
        "good!",
        "windy :|",
        "sunny.",
        "cold, like 15 degrees (celcius, ofc.)."
    ])
    return f"{city} weather is {adj}"


@mcp.tool()
def get_location(person: str) -> str:
    """
    Returns the current location of a person
    :param person: The name of the person
    """
    cities = [
        "São Paulo, Brazil",
        "Lima, Peru",
        "Bogotá, Colombia",
        "Rio de Janeiro, Brazil",
        "Santiago, Chile",
        "Caracas, Venezuela",
        "Buenos Aires, Argentina",
        "Brasília, Brazil",
        "Medellín, Colombia",
        "Guayaquil, Ecuador",
        "Fortaleza, Brazil",
        "Salvador, Brazil",
        "Belo Horizonte, Brazil",
        "Manaus, Brazil",
    ]
    return choice(cities)



if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
