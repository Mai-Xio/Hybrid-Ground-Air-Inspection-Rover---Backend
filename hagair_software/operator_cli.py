from __future__ import annotations

from hagair_software.main_pipeline import run_pipeline


def main():
    print("HAGAIR v3.0 Operator CLI")
    print("Choose scenario: normal / pollution / flood / fire / night / industrial")
    scenario = input("Scenario [normal]: ").strip() or "normal"
    print("Choose profile: general / drainage / road_safety / flood_zone / air_quality / night_ir / soil_survey / industrial_chemical")
    profile = input("Profile [general]: ").strip() or "general"
    steps = input("Steps [20]: ").strip() or "20"
    run_pipeline(steps=int(steps), scenario=scenario, profile=profile, dashboard=True)


if __name__ == "__main__":
    main()
