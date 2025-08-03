from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
import uuid
import hashlib
import json
import secrets
from typing import List, Dict, Any

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enable this during testing only
DEV_MODE = True

# Simple test endpoint
@app.get("/")
def read_root():
    return {"message": "Cave Explorer API is running!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
    
# --- Models ---
class StartGameRequest(BaseModel):
    player_name: str
    seed: str = None  # Optional player-provided seed for extra entropy

class TakeTurnRequest(BaseModel):
    player_name: str
    session_id: str
    chosen_path_id: int
    insurance: bool = False

class PathOption:
    def __init__(self, id, type, reward, is_trap=False):
        self.id = id
        self.type = type
        self.reward = reward
        self.is_trap = is_trap

    def to_dict(self, include_trap=False):
        risk_map = {
            "standard": "Low",
            "premium": "Medium", 
            "hrhr": "High"
        }
        trap_chance_map = {
            "standard": "15%",
            "premium": "30%",
            "hrhr": "50%"
        }
        data = {
            "id": self.id,
            "type": self.type,
            "reward": round(self.reward, 2),
            "risk_level": risk_map[self.type],
            "trap_chance": trap_chance_map[self.type]
        }
        if include_trap:
            data["is_trap"] = self.is_trap
        return data

    def to_serializable_dict(self):
        """For hashing/commitment purposes"""
        return {
            "type": self.type,
            "reward": self.reward,
            "is_trap": self.is_trap
        }

# --- Game Configuration ---
MAX_TURNS = 6
INSURANCE_RATE = 0.3

# --- Provably Fair System ---
class ProvenanceSystem:
    @staticmethod
    def generate_server_seed() -> str:
        """Generate cryptographically secure server seed"""
        return secrets.token_hex(32)  # 64 character hex string
    
    @staticmethod
    def create_combined_seed(server_seed: str, client_seed: str = None, session_id: str = "") -> str:
        """Combine server + client seeds for deterministic randomness"""
        if not client_seed:
            client_seed = "default_client_seed"
        
        combined = f"{server_seed}:{client_seed}:{session_id}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    @staticmethod
    def generate_all_game_paths(combined_seed: str, max_turns: int) -> List[List[PathOption]]:
        """Pre-generate ALL paths for entire game using deterministic seed"""
        # Use combined seed to initialize deterministic random state
        rng = random.Random(combined_seed)
        
        all_turns_paths = []
        
        for turn in range(max_turns):
            turn_paths = []
            total_paths = rng.choice([3, 4])
            
            # Always include 1 standard path first
            std_reward = round(rng.uniform(0.1, 0.25), 2)
            std_trap = rng.random() < 0.15
            turn_paths.append(PathOption(-1, "standard", std_reward, is_trap=std_trap))
            
            # Add remaining paths
            while len(turn_paths) < total_paths:
                path_type = rng.choices(
                    ["standard", "premium", "hrhr"], 
                    weights=[0.6, 0.25, 0.15]
                )[0]

                if path_type == "standard":
                    reward = round(rng.uniform(0.1, 0.25), 2)
                    trap_chance = 0.15
                elif path_type == "premium":
                    reward = round(rng.uniform(0.3, 0.5), 2)
                    trap_chance = 0.30
                else:  # hrhr
                    reward = round(rng.uniform(0.5, 0.75), 2)
                    trap_chance = 0.50

                is_trap = rng.random() < trap_chance
                turn_paths.append(PathOption(-1, path_type, reward, is_trap=is_trap))

            # Shuffle and assign final IDs for this turn
            rng.shuffle(turn_paths)
            for i, path in enumerate(turn_paths):
                path.id = i
            
            all_turns_paths.append(turn_paths)
        
        return all_turns_paths
    
    @staticmethod
    def create_commitment_hash(all_paths: List[List[PathOption]], server_seed: str) -> str:
        """Create cryptographic commitment of all game paths"""
        # Serialize all paths in a deterministic way
        paths_data = []
        for turn_idx, turn_paths in enumerate(all_paths):
            turn_data = {
                "turn": turn_idx + 1,
                "paths": [path.to_serializable_dict() for path in turn_paths]
            }
            paths_data.append(turn_data)
        
        # Create commitment hash
        commitment_data = {
            "server_seed": server_seed,
            "all_paths": paths_data
        }
        
        commitment_string = json.dumps(commitment_data, sort_keys=True)
        return hashlib.sha256(commitment_string.encode()).hexdigest()

# --- Game State ---
sessions = {}  # session_id -> game state

@app.post("/start_game")
def start_game(req: StartGameRequest):
    session_id = str(uuid.uuid4())
    
    # Generate provably fair setup
    server_seed = ProvenanceSystem.generate_server_seed()
    combined_seed = ProvenanceSystem.create_combined_seed(
        server_seed, req.seed, session_id
    )
    
    # Pre-generate ALL paths for the entire game
    all_game_paths = ProvenanceSystem.generate_all_game_paths(combined_seed, MAX_TURNS)
    
    # Create commitment hash (this would be stored on-chain in blockchain version)
    commitment_hash = ProvenanceSystem.create_commitment_hash(all_game_paths, server_seed)
    
    sessions[session_id] = {
        "player_name": req.player_name,
        "turn": 1,
        "rewards": 0.0,
        "alive": True,
        "history": [],
        
        # Provably Fair Data
        "server_seed": server_seed,
        "client_seed": req.seed,
        "combined_seed": combined_seed,
        "commitment_hash": commitment_hash,
        "all_game_paths": all_game_paths,  # Pre-generated paths
        "game_completed": False
    }
    
    # Get first turn options
    first_turn_options = all_game_paths[0]
    
    response = build_game_state_response(
        session_id, 
        f"Welcome {req.player_name}! Game created with provable fairness.", 
        first_turn_options
    )
    
    # Add provenance info to response
    response["provenance"] = {
        "commitment_hash": commitment_hash,
        "client_seed_used": req.seed or "default_client_seed",
        "session_id": session_id
    }
    
    return response

@app.post("/take_turn")
def take_turn(req: TakeTurnRequest):
    session = sessions.get(req.session_id)
    if not session:
        return {"error": "Invalid session ID."}
    
    if not session["alive"]:
        return {"error": "Game already ended."}

    if session["turn"] > MAX_TURNS:
        return {"error": "Maximum turns exceeded."}

    # Get current turn's pre-generated paths
    current_turn_paths = session["all_game_paths"][session["turn"] - 1]
    
    # Find chosen path
    chosen = next((p for p in current_turn_paths if p.id == req.chosen_path_id), None)
    if not chosen:
        return {"error": "Invalid path choice."}

    # Calculate insurance cost (based on current rewards you're protecting)
    insurance_cost = 0.0
    can_use_insurance = (
        session["turn"] > 1 and  # Can't use insurance on turn 1
        chosen.type != "hrhr" and  # Can't insure HRHR paths
        session["rewards"] > 0  # Need rewards to insure
    )
    
    if req.insurance and session["turn"] == 1:
        return {"error": "Insurance not available on turn 1."}
    
    if req.insurance and chosen.type == "hrhr":
        return {"error": "Insurance not available for High Risk High Reward paths."}
    
    if req.insurance and session["rewards"] <= 0:
        return {"error": "No rewards to insure."}

    if req.insurance and can_use_insurance:
        insurance_cost = INSURANCE_RATE * session["rewards"]

    outcome_parts = []
    turn_loss = False

    # Process the chosen path (using pre-generated result)
    if chosen.is_trap:
        if req.insurance and can_use_insurance:
            # Insurance saves the player
            session["rewards"] -= insurance_cost
            outcome_parts.append(f"💀 TRAP! But insurance saved you!")
            outcome_parts.append(f"Insurance cost: -{insurance_cost:.2f} tokens")
        else:
            # Player dies
            session["alive"] = False
            session["rewards"] = 0  # Lose all rewards
            turn_loss = True
            outcome_parts.append(f"💀 TRAP! You died on turn {session['turn']}.")
            outcome_parts.append("All rewards lost!")
    else:
        # Safe path - gain reward
        session["rewards"] += chosen.reward
        outcome_parts.append(f"✅ Safe! Found {chosen.reward:.2f} tokens.")
        
        if req.insurance and can_use_insurance:
            session["rewards"] -= insurance_cost
            outcome_parts.append(f"Insurance cost: -{insurance_cost:.2f} tokens")

    # Record turn history
    session["history"].append({
        "turn": session["turn"],
        "choice": chosen.to_dict(include_trap=True),  # Always include for history
        "insurance_used": req.insurance and can_use_insurance,
        "insurance_cost": insurance_cost if req.insurance and can_use_insurance else 0,
        "trap_hit": chosen.is_trap,
        "survived": session["alive"],
        "outcome": " ".join(outcome_parts)
    })

    # Prepare for next turn or end game
    next_turn_options = []
    if session["alive"]:
        session["turn"] += 1
        
        if session["turn"] <= MAX_TURNS:
            # Get pre-generated options for next turn
            next_turn_options = session["all_game_paths"][session["turn"] - 1]
            final_outcome = " ".join(outcome_parts) + f" (Turn {session['turn']-1} complete)"
        else:
            # Game won!
            session["alive"] = False  # End the game
            session["game_completed"] = True
            final_outcome = " ".join(outcome_parts) + f" 🎉 VICTORY! You completed all {MAX_TURNS} turns!"
    else:
        # Game lost
        session["game_completed"] = True
        final_outcome = " ".join(outcome_parts) + " 💀 Game Over!"

    return build_game_state_response(req.session_id, final_outcome, next_turn_options)

# --- Provenance Endpoints ---
@app.get("/reveal_game/{session_id}")
def reveal_game_provenance(session_id: str):
    """Reveal all game data after completion to prove fairness"""
    session = sessions.get(session_id)
    if not session:
        return {"error": "Session not found"}
    
    if not session.get("game_completed", False):
        return {"error": "Game must be completed before revealing provenance"}
    
    # Serialize all pre-generated paths for verification
    all_paths_revealed = []
    for turn_idx, turn_paths in enumerate(session["all_game_paths"]):
        turn_data = {
            "turn": turn_idx + 1,
            "paths": [path.to_serializable_dict() for path in turn_paths]
        }
        all_paths_revealed.append(turn_data)
    
    return {
        "session_id": session_id,
        "provenance": {
            "server_seed": session["server_seed"],
            "client_seed": session["client_seed"],
            "combined_seed": session["combined_seed"],
            "commitment_hash": session["commitment_hash"],
            "all_paths_revealed": all_paths_revealed
        },
        "game_summary": {
            "player": session["player_name"],
            "final_rewards": session["rewards"],
            "survived": session["alive"],
            "turns_played": len(session["history"]),
            "history": session["history"]
        },
        "verification_instructions": {
            "step_1": "Use the server_seed and client_seed to regenerate the combined_seed",
            "step_2": "Use combined_seed to regenerate all game paths",
            "step_3": "Compare regenerated paths with revealed paths - they should match exactly",
            "step_4": "Verify that commitment_hash matches hash of revealed data + server_seed"
        }
    }

@app.post("/verify_game")
def verify_game_fairness(verification_data: Dict[str, Any]):
    """Independent verification endpoint - anyone can verify game fairness"""
    try:
        server_seed = verification_data["server_seed"]
        client_seed = verification_data.get("client_seed")
        session_id = verification_data["session_id"]
        claimed_paths = verification_data["all_paths_revealed"]
        claimed_commitment = verification_data["commitment_hash"]
        
        # Recreate the game using the seeds
        combined_seed = ProvenanceSystem.create_combined_seed(server_seed, client_seed, session_id)
        regenerated_paths = ProvenanceSystem.generate_all_game_paths(combined_seed, MAX_TURNS)
        
        # Convert to comparable format
        regenerated_serialized = []
        for turn_idx, turn_paths in enumerate(regenerated_paths):
            turn_data = {
                "turn": turn_idx + 1,
                "paths": [path.to_serializable_dict() for path in turn_paths]
            }
            regenerated_serialized.append(turn_data)
        
        # Verify paths match
        paths_match = regenerated_serialized == claimed_paths
        
        # Verify commitment hash
        recreated_commitment = ProvenanceSystem.create_commitment_hash(regenerated_paths, server_seed)
        commitment_matches = recreated_commitment == claimed_commitment
        
        return {
            "verification_result": {
                "paths_match": paths_match,
                "commitment_matches": commitment_matches,
                "game_is_fair": paths_match and commitment_matches
            },
            "details": {
                "regenerated_combined_seed": combined_seed,
                "recreated_commitment_hash": recreated_commitment,
                "paths_verified": len(regenerated_serialized)
            }
        }
        
    except Exception as e:
        return {"error": f"Verification failed: {str(e)}"}

# --- Helper Functions ---
def build_game_state_response(session_id, outcome, options):
    session = sessions[session_id]
    
    # Calculate insurance cost preview (based on current rewards)
    insurance_cost_preview = None
    has_rewards_to_insure = session["rewards"] > 0
    can_show_insurance = (
        session["turn"] > 1 and 
        session["alive"] and 
        has_rewards_to_insure
    )
    
    if can_show_insurance:
        insurance_cost_preview = round(INSURANCE_RATE * session["rewards"], 2)
    
    # Mark which paths allow insurance
    for option in options:
        option.allows_insurance = (
            session["turn"] > 1 and 
            option.type != "hrhr" and 
            has_rewards_to_insure
        )

    return {
        "session_id": session_id,
        "player_name": session["player_name"],
        "turn": session["turn"],
        "max_turns": MAX_TURNS,
        "rewards": round(session["rewards"], 2),
        "alive": session["alive"],
        "can_use_insurance": can_show_insurance,
        "insurance_cost_preview": insurance_cost_preview,
        "path_options": [
            {**opt.to_dict(include_trap=DEV_MODE), "allows_insurance": getattr(opt, 'allows_insurance', False)} 
            for opt in options
        ],
        "last_outcome": outcome,
        "history": session["history"]
    }

# --- Additional Endpoints ---
@app.get("/game_state/{session_id}")
def get_game_state(session_id: str):
    """Get current game state without taking a turn"""
    session = sessions.get(session_id)
    if not session:
        return {"error": "Session not found"}
    
    current_options = []
    if session["alive"] and session["turn"] <= MAX_TURNS:
        current_options = session["all_game_paths"][session["turn"] - 1]
    
    return build_game_state_response(
        session_id, 
        "Current game state", 
        current_options
    )

@app.delete("/session/{session_id}")
def end_session(session_id: str):
    """Manually end a game session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session ended"}
    return {"error": "Session not found"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "active_sessions": len(sessions),
        "dev_mode": DEV_MODE,
        "provably_fair": True
    }