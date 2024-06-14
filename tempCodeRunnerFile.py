async def execute_regular_command(interaction: discord.Interaction, directory: str, command_name: str, cooldown_hours: int, last_command_usage: list):
    user_id = interaction.user.id
    user = fetch_or_register_user(user_id)

    if not user:
        await interaction.response.send_message("Failed to fetch or register user.", ephemeral=True)
        return

    client = None  # Initialize client variable

    try:
        # Check cooldown first
        can_use, remaining_hours, remaining_minutes = await can_use_command(user_id, command_name, last_command_usage, cooldown_hours)

        if not can_use:
            await interaction.response.send_message(f"You can use this command only once every {cooldown_hours} hours. Now {remaining_hours} hours {remaining_minutes} minutes remaining.", ephemeral=True)
            return

        # Check points
        current_points = user.get('points', 0)
        if current_points < 2:
            await interaction.response.send_message("You don't have enough points to use this command.", ephemeral=True)
            return

        # Deduct points
        new_points = current_points - 2
        if new_points < 0:
            new_points = 0  # Ensure points don't go negative

        # Connect to MongoDB
        client = pymongo.MongoClient(MONGODB_CONNECTION_STRING)
        db = client['db_discord']
        collection = db['tbl_discord']

        # Update points in MongoDB
        collection.update_one({'userid': user_id}, {'$set': {'points': new_points}})

        await interaction.response.send_message(f"Your 2 points have been deducted. Your remaining points: {new_points}.", ephemeral=True)

        # Log command usage and handle sending a file if available
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cooldown_time = (datetime.now() + timedelta(hours=cooldown_hours)).strftime("%Y-%m-%d %H:%M:%S")
        files = [file for file in os.listdir(directory) if file.endswith('.txt')]
        
        if files:
            random_file = random.choice(files)
            file_path = os.path.join(directory, random_file)

            new_entry = {
                'user_id': user_id,
                'user_name': interaction.user.name,
                'command_used': command_name,
                'time': timestamp,
                'cooldown_time': cooldown_time,
                'file_name': random_file  # Update with actual file name
            }
            last_command_usage.append(new_entry)
            save_cooldowns(last_command_usage)

            try:
                await interaction.user.send(file=discord.File(file_path))
                await log_command_usage(interaction, command_name, random_file)

            except discord.errors.Forbidden:
                await interaction.response.send_message("I cannot send you a direct message. Please enable DMs and try again.", ephemeral=True)

        else:
            await interaction.response.send_message(f"No {command_name} cookie files are available right now. Please try again later.", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"Failed to deduct points or send cookie: {e}", ephemeral=True)

    finally:
        if client:
            client.close()
