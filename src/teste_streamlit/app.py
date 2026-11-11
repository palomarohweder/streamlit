from __future__ import annotations

import smtplib
from collections.abc import Callable

import streamlit as st
from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from teste_streamlit.auth import (
    AuthenticationError,
    authenticate,
    hash_password,
    register_user,
    request_password_reset,
    reset_password,
    verify_password,
)
from teste_streamlit.database import get_engine, initialize_database
from teste_streamlit.models import Equipment, Experiment, Favorite, Folder, User

EQUIPMENT_FORM_KEYS = (
    "equipment_new_name",
    "equipment_new_category",
    "equipment_new_description",
    "equipment_new_quantity",
    "equipment_new_bench",
    "equipment_new_cabinet_door",
    "equipment_new_drawer",
)


def _commit(session: Session, success_message: str) -> bool:
    try:
        session.commit()
    except SQLAlchemyError as error:
        session.rollback()
        st.error(f"Não foi possível salvar. Verifique os dados. ({type(error).__name__})")
        return False
    st.success(success_message)
    return True


def _consume_form_feedback(form_id: str, field_keys: tuple[str, ...]) -> None:
    if st.session_state.pop(f"clear_{form_id}", False):
        for key in field_keys:
            st.session_state.pop(key, None)
    message = st.session_state.pop(f"success_{form_id}", None)
    if message:
        st.success(message)


def _rerun_form_feedback(form_id: str, message: str) -> None:
    st.session_state[f"clear_{form_id}"] = True
    st.session_state[f"success_{form_id}"] = message
    st.rerun()


def _auth_screen(session: Session) -> None:
    st.title("Organizador de Laboratório")
    st.caption("Laboratório de Física · IFC Campus Blumenau")
    action = st.radio(
        "Acesso",
        ("Entrar", "Criar conta", "Esqueci a senha", "Redefinir senha"),
        horizontal=True,
    )

    if action == "Entrar":
        with st.form("login_form"):
            email = st.text_input("E-mail institucional")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar", type="primary")
        if submitted:
            try:
                user = authenticate(session, email, password)
            except AuthenticationError as error:
                st.error(str(error))
            else:
                st.session_state["user_id"] = user.id
                st.rerun()

    elif action == "Criar conta":
        st.info(
            "Escolha seu perfil e use o e-mail institucional correspondente. "
            "Docentes podem gerenciar equipamentos e experimentos; discentes "
            "podem consultar e organizar favoritos."
        )
        with st.form("register_form"):
            full_name = st.text_input("Nome completo")
            email = st.text_input("E-mail institucional")
            profile = st.selectbox("Perfil", ("Discente", "Docente"))
            password = st.text_input("Senha (mínimo de 10 caracteres)", type="password")
            confirmation = st.text_input("Confirme a senha", type="password")
            submitted = st.form_submit_button("Criar conta", type="primary")
        if submitted:
            if password != confirmation:
                st.error("As senhas não coincidem.")
            else:
                try:
                    role = "student" if profile == "Discente" else "teacher"
                    register_user(session, full_name, email, password, role)
                    _commit(session, "Conta criada. Você já pode entrar.")
                except AuthenticationError as error:
                    session.rollback()
                    st.error(str(error))
                except SQLAlchemyError as error:
                    session.rollback()
                    st.error(f"Não foi possível criar a conta. ({type(error).__name__})")

    elif action == "Esqueci a senha":
        st.write("Informe seu e-mail institucional para receber um código de redefinição.")
        with st.form("request_reset_form"):
            email = st.text_input("E-mail institucional")
            submitted = st.form_submit_button("Enviar código", type="primary")
        if submitted:
            try:
                request_password_reset(session, email)
                session.commit()
                st.success(
                    "Se houver uma conta para esse e-mail, enviaremos as instruções "
                    "de recuperação."
                )
            except (RuntimeError, OSError, smtplib.SMTPException, ValueError) as error:
                session.rollback()
                st.error(
                    "Não foi possível enviar o e-mail de recuperação. "
                    f"Verifique a configuração SMTP. ({type(error).__name__})"
                )
            except SQLAlchemyError as error:
                session.rollback()
                st.error(f"Falha ao solicitar a recuperação. ({type(error).__name__})")

    else:
        with st.form("reset_form"):
            email = st.text_input("E-mail institucional")
            token = st.text_input("Código recebido por e-mail")
            password = st.text_input("Nova senha (mínimo de 10 caracteres)", type="password")
            confirmation = st.text_input("Confirme a nova senha", type="password")
            submitted = st.form_submit_button("Redefinir senha", type="primary")
        if submitted:
            if password != confirmation:
                st.error("As senhas não coincidem.")
            else:
                try:
                    reset_password(session, email, token, password)
                    _commit(session, "Senha redefinida. Entre com sua nova senha.")
                except AuthenticationError as error:
                    session.rollback()
                    st.error(str(error))
                except SQLAlchemyError as error:
                    session.rollback()
                    st.error(f"Não foi possível redefinir a senha. ({type(error).__name__})")


def _dashboard(session: Session, user: User) -> None:
    total_equipment = len(session.scalars(select(Equipment)).all())
    total_experiments = len(session.scalars(select(Experiment)).all())
    total_favorites = len(
        session.scalars(select(Favorite).where(Favorite.user_id == user.id)).all()
    )

    st.title(f"Olá, {user.full_name.split()[0]}")
    st.caption("Consulte os equipamentos do laboratório e planeje seus experimentos.")
    first, second, third = st.columns(3)
    first.metric("Equipamentos", total_equipment)
    second.metric("Experimentos", total_experiments)
    third.metric("Seus favoritos", total_favorites)

    st.subheader("Localização dos equipamentos")
    equipment = session.scalars(select(Equipment).order_by(Equipment.name)).all()
    if not equipment:
        st.info("Ainda não há equipamentos cadastrados.")
    else:
        st.dataframe(
            [
                {
                    "Equipamento": item.name,
                    "Categoria": item.category,
                    "Quantidade": item.quantity,
                    "Bancada": item.bench or "—",
                    "Porta": item.cabinet_door or "—",
                    "Gaveta": item.drawer or "—",
                }
                for item in equipment
            ],
            width="stretch",
            hide_index=True,
        )


def _equipment_page(session: Session, user: User) -> None:
    _consume_form_feedback("equipment_create", EQUIPMENT_FORM_KEYS)
    st.title("Equipamentos")
    equipment = session.scalars(select(Equipment).order_by(Equipment.name)).all()
    query = st.text_input("Buscar por nome, categoria ou localização")
    filtered = [
        item
        for item in equipment
        if query.casefold()
        in " ".join(
            (
                item.name,
                item.category,
                item.description,
                item.bench,
                item.cabinet_door,
                item.drawer,
            )
        ).casefold()
    ]
    _equipment_table(filtered)

    if user.role != "teacher":
        return

    create_tab, edit_tab = st.tabs(("Cadastrar", "Editar ou excluir"))
    with create_tab:
        with st.form("create_equipment"):
            name = st.text_input("Nome do equipamento", key=EQUIPMENT_FORM_KEYS[0])
            category = st.text_input("Categoria", key=EQUIPMENT_FORM_KEYS[1])
            description = st.text_area("Descrição", key=EQUIPMENT_FORM_KEYS[2])
            quantity = st.number_input(
                "Quantidade",
                min_value=1,
                step=1,
                key=EQUIPMENT_FORM_KEYS[3],
            )
            bench = st.text_input("Bancada", key=EQUIPMENT_FORM_KEYS[4])
            cabinet_door = st.text_input(
                "Porta do armário", key=EQUIPMENT_FORM_KEYS[5]
            )
            drawer = st.text_input("Gaveta", key=EQUIPMENT_FORM_KEYS[6])
            submitted = st.form_submit_button("Cadastrar equipamento", type="primary")
        if submitted:
            if not name.strip():
                st.error("Informe o nome do equipamento.")
            elif any(
                item.name.casefold() == name.strip().casefold()
                and item.category.casefold() == category.strip().casefold()
                and item.bench.casefold() == bench.strip().casefold()
                and item.cabinet_door.casefold() == cabinet_door.strip().casefold()
                and item.drawer.casefold() == drawer.strip().casefold()
                for item in equipment
            ):
                st.error(
                    "Este equipamento já está cadastrado nesse local. "
                    "Edite o registro existente para atualizar a quantidade."
                )
            else:
                session.add(
                    Equipment(
                        name=name.strip(),
                        category=category.strip(),
                        description=description.strip(),
                        quantity=int(quantity),
                        bench=bench.strip(),
                        cabinet_door=cabinet_door.strip(),
                        drawer=drawer.strip(),
                    )
                )
                if _commit(session, "Equipamento cadastrado."):
                    _rerun_form_feedback(
                        "equipment_create", "Equipamento cadastrado com sucesso."
                    )

    with edit_tab:
        if not equipment:
            st.info("Cadastre um equipamento para habilitar a edição.")
            return
        equipment_by_id = {item.id: item for item in equipment}
        if (
            not isinstance(st.session_state.get("equipment_to_edit"), int)
            or st.session_state["equipment_to_edit"] not in equipment_by_id
        ):
            st.session_state.pop("equipment_to_edit", None)
        selected_id = st.selectbox(
            "Equipamento",
            list(equipment_by_id),
            format_func=lambda item_id: (
                f"{equipment_by_id[item_id].name} · #{item_id}"
            ),
            key="equipment_to_edit",
        )
        selected = equipment_by_id[selected_id]
        with st.form("edit_equipment"):
            name = st.text_input("Nome", value=selected.name)
            category = st.text_input("Categoria", value=selected.category)
            description = st.text_area("Descrição", value=selected.description)
            quantity = st.number_input(
                "Quantidade", min_value=1, step=1, value=selected.quantity
            )
            bench = st.text_input("Bancada", value=selected.bench)
            cabinet_door = st.text_input("Porta do armário", value=selected.cabinet_door)
            drawer = st.text_input("Gaveta", value=selected.drawer)
            update = st.form_submit_button("Salvar alterações", type="primary")
        if update:
            if not name.strip():
                st.error("Informe o nome do equipamento.")
            else:
                selected.name = name.strip()
                selected.category = category.strip()
                selected.description = description.strip()
                selected.quantity = int(quantity)
                selected.bench = bench.strip()
                selected.cabinet_door = cabinet_door.strip()
                selected.drawer = drawer.strip()
                if _commit(session, "Equipamento atualizado."):
                    st.rerun()
        with st.form("delete_equipment"):
            confirm = st.checkbox(f"Confirmo a exclusão de {selected.name}")
            delete = st.form_submit_button("Excluir equipamento")
        if delete:
            if not confirm:
                st.error("Confirme a exclusão antes de continuar.")
            else:
                session.execute(
                    sql_delete(Favorite).where(
                        Favorite.equipment_id == selected.id
                    )
                )
                session.delete(selected)
                if _commit(session, "Equipamento excluído."):
                    st.rerun()


def _equipment_table(items: list[Equipment]) -> None:
    if not items:
        st.info("Nenhum equipamento encontrado.")
        return
    st.dataframe(
        [
            {
                "Equipamento": item.name,
                "Categoria": item.category,
                "Descrição": item.description,
                "Quantidade": item.quantity,
                "Bancada": item.bench or "—",
                "Porta": item.cabinet_door or "—",
                "Gaveta": item.drawer or "—",
            }
            for item in items
        ],
        width="stretch",
        hide_index=True,
    )


def _experiment_page(session: Session, user: User) -> None:
    experiment_form_keys = (
        "experiment_new_title",
        "experiment_new_description",
        "experiment_new_materials",
        "experiment_new_procedure",
        "experiment_new_safety_notes",
    )
    _consume_form_feedback("experiment_create", experiment_form_keys)
    st.title("Experimentos")
    experiments = session.scalars(select(Experiment).order_by(Experiment.title)).all()
    query = st.text_input("Buscar por título, descrição ou conteúdo")
    filtered = [
        item
        for item in experiments
        if query.casefold()
        in " ".join(
            (item.title, item.description, item.materials, item.procedure, item.safety_notes)
        ).casefold()
    ]
    for experiment in filtered:
        with st.expander(experiment.title):
            st.write(experiment.description or "Sem descrição.")
            st.markdown(f"**Materiais**\n\n{experiment.materials or 'Não informado.'}")
            st.markdown(f"**Procedimento**\n\n{experiment.procedure or 'Não informado.'}")
            st.markdown(
                f"**Segurança**\n\n{experiment.safety_notes or 'Não informado.'}"
            )
    if not filtered:
        st.info("Nenhum experimento encontrado.")

    if user.role != "teacher":
        return

    create_tab, edit_tab = st.tabs(("Cadastrar", "Editar ou excluir"))
    with create_tab:
        with st.form("create_experiment"):
            title = st.text_input("Título", key=experiment_form_keys[0])
            description = st.text_area(
                "Descrição", key=experiment_form_keys[1]
            )
            materials = st.text_area("Materiais", key=experiment_form_keys[2])
            procedure = st.text_area("Procedimento", key=experiment_form_keys[3])
            safety_notes = st.text_area(
                "Cuidados de segurança", key=experiment_form_keys[4]
            )
            submitted = st.form_submit_button("Cadastrar experimento", type="primary")
        if submitted:
            if not title.strip():
                st.error("Informe o título do experimento.")
            else:
                session.add(
                    Experiment(
                        title=title.strip(),
                        description=description.strip(),
                        materials=materials.strip(),
                        procedure=procedure.strip(),
                        safety_notes=safety_notes.strip(),
                        created_by_id=user.id,
                    )
                )
                if _commit(session, "Experimento cadastrado."):
                    _rerun_form_feedback(
                        "experiment_create", "Experimento cadastrado com sucesso."
                    )

    with edit_tab:
        if not experiments:
            st.info("Cadastre um experimento para habilitar a edição.")
            return
        experiments_by_id = {item.id: item for item in experiments}
        if not isinstance(st.session_state.get("experiment_to_edit"), int):
            st.session_state.pop("experiment_to_edit", None)
        elif st.session_state["experiment_to_edit"] not in experiments_by_id:
            st.session_state.pop("experiment_to_edit", None)
        selected_id = st.selectbox(
            "Experimento",
            list(experiments_by_id),
            format_func=lambda item_id: (
                f"{experiments_by_id[item_id].title} · #{item_id}"
            ),
            key="experiment_to_edit",
        )
        selected = experiments_by_id[selected_id]
        with st.form("edit_experiment"):
            title = st.text_input("Título", value=selected.title)
            description = st.text_area("Descrição", value=selected.description)
            materials = st.text_area("Materiais", value=selected.materials)
            procedure = st.text_area("Procedimento", value=selected.procedure)
            safety_notes = st.text_area(
                "Cuidados de segurança", value=selected.safety_notes
            )
            update = st.form_submit_button("Salvar alterações", type="primary")
        if update:
            if not title.strip():
                st.error("Informe o título do experimento.")
            else:
                selected.title = title.strip()
                selected.description = description.strip()
                selected.materials = materials.strip()
                selected.procedure = procedure.strip()
                selected.safety_notes = safety_notes.strip()
                if _commit(session, "Experimento atualizado."):
                    st.rerun()
        with st.form("delete_experiment"):
            confirm = st.checkbox(f"Confirmo a exclusão de {selected.title}")
            delete = st.form_submit_button("Excluir experimento")
        if delete:
            if not confirm:
                st.error("Confirme a exclusão antes de continuar.")
            else:
                session.execute(
                    sql_delete(Favorite).where(
                        Favorite.experiment_id == selected.id
                    )
                )
                session.delete(selected)
                if _commit(session, "Experimento excluído."):
                    st.rerun()


def _folder_page(session: Session, user: User) -> None:
    st.title("Pastas e favoritos")
    folders = session.scalars(
        select(Folder).where(Folder.user_id == user.id).order_by(Folder.name)
    ).all()
    favorites = session.scalars(
        select(Favorite).where(Favorite.user_id == user.id).order_by(Favorite.id)
    ).all()
    folder_names = {folder.id: folder.name for folder in folders}
    equipment_by_id = {
        item.id: item
        for item in session.scalars(select(Equipment)).all()
    }
    experiments_by_id = {
        item.id: item
        for item in session.scalars(select(Experiment)).all()
    }

    st.subheader("Minhas pastas")
    if folders:
        st.dataframe(
            [
                {"Pasta": folder.name, "Descrição": folder.description}
                for folder in folders
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.caption("Você ainda não criou pastas.")

    add_folder, edit_folder = st.tabs(("Criar pasta", "Editar ou excluir pasta"))
    with add_folder:
        with st.form("create_folder"):
            name = st.text_input("Nome da pasta")
            description = st.text_input("Descrição")
            submitted = st.form_submit_button("Criar pasta", type="primary")
        if submitted:
            if not name.strip():
                st.error("Informe o nome da pasta.")
            else:
                session.add(
                    Folder(
                        user_id=user.id,
                        name=name.strip(),
                        description=description.strip(),
                    )
                )
                if _commit(session, "Pasta criada."):
                    st.rerun()
    with edit_folder:
        if not folders:
            st.info("Crie uma pasta para habilitar a edição.")
        else:
            if (
                not isinstance(st.session_state.get("folder_to_edit"), int)
                or st.session_state["folder_to_edit"] not in folder_names
            ):
                st.session_state.pop("folder_to_edit", None)
            selected_folder_id = st.selectbox(
                "Pasta",
                list(folder_names),
                format_func=lambda folder_id: folder_names[folder_id],
                key="folder_to_edit",
            )
            selected_folder = next(
                folder for folder in folders if folder.id == selected_folder_id
            )
            with st.form("edit_folder"):
                name = st.text_input("Nome", value=selected_folder.name)
                description = st.text_input(
                    "Descrição", value=selected_folder.description
                )
                update = st.form_submit_button("Salvar alterações", type="primary")
            if update:
                if not name.strip():
                    st.error("Informe o nome da pasta.")
                else:
                    selected_folder.name = name.strip()
                    selected_folder.description = description.strip()
                    if _commit(session, "Pasta atualizada."):
                        st.rerun()
            with st.form("delete_folder"):
                confirm = st.checkbox(f"Confirmo a exclusão de {selected_folder.name}")
                delete = st.form_submit_button("Excluir pasta")
            if delete:
                if not confirm:
                    st.error("Confirme a exclusão antes de continuar.")
                else:
                    session.delete(selected_folder)
                    if _commit(session, "Pasta excluída."):
                        st.rerun()

    st.divider()
    st.subheader("Favoritos")
    for favorite in favorites:
        target = (
            equipment_by_id.get(favorite.equipment_id)
            if favorite.equipment_id is not None
            else experiments_by_id.get(favorite.experiment_id)
        )
        label = target.name if isinstance(target, Equipment) else (
            target.title if isinstance(target, Experiment) else "Item removido"
        )
        st.write(f"★ {label} · Pasta: {folder_names.get(favorite.folder_id, 'Sem pasta')}")

    add_favorite, edit_favorite, remove_favorite = st.tabs(
        ("Adicionar favorito", "Mover para pasta", "Remover favorito")
    )
    with add_favorite:
        target_type = st.radio(
            "Tipo de item", ("Equipamento", "Experimento"), horizontal=True
        )
        targets = (
            list(equipment_by_id.values())
            if target_type == "Equipamento"
            else list(experiments_by_id.values())
        )
        if not targets:
            st.info(f"Não há {target_type.lower()} cadastrados.")
        else:
            target_by_id = {item.id: item for item in targets}
            target_key = (
                "favorite_equipment_target"
                if target_type == "Equipamento"
                else "favorite_experiment_target"
            )
            if (
                not isinstance(st.session_state.get(target_key), int)
                or st.session_state[target_key] not in target_by_id
            ):
                st.session_state.pop(target_key, None)
            with st.form("add_favorite"):
                selected_target_id = st.selectbox(
                    target_type,
                    list(target_by_id),
                    format_func=lambda item_id: (
                        target_by_id[item_id].name
                        if isinstance(target_by_id[item_id], Equipment)
                        else target_by_id[item_id].title
                    ),
                    key=target_key,
                )
                selected_folder_id = st.selectbox(
                    "Pasta",
                    [None, *[folder.id for folder in folders]],
                    format_func=lambda folder_id: (
                        "Sem pasta" if folder_id is None else folder_names[folder_id]
                    ),
                )
                submitted = st.form_submit_button("Adicionar aos favoritos")
            if submitted:
                selected_target = target_by_id[selected_target_id]
                equipment_id = (
                    selected_target.id
                    if isinstance(selected_target, Equipment)
                    else None
                )
                experiment_id = (
                    selected_target.id
                    if isinstance(selected_target, Experiment)
                    else None
                )
                duplicate = session.scalar(
                    select(Favorite).where(
                        Favorite.user_id == user.id,
                        Favorite.equipment_id == equipment_id,
                        Favorite.experiment_id == experiment_id,
                    )
                )
                if duplicate:
                    st.error("Este item já está nos seus favoritos.")
                else:
                    session.add(
                        Favorite(
                            user_id=user.id,
                            equipment_id=equipment_id,
                            experiment_id=experiment_id,
                            folder_id=selected_folder_id,
                        )
                    )
                    if _commit(session, "Favorito adicionado."):
                        st.rerun()
    with edit_favorite:
        if not favorites:
            st.info("Adicione um favorito para habilitar a organização em pastas.")
        else:
            favorites_by_id = {item.id: item for item in favorites}
            if (
                not isinstance(st.session_state.get("favorite_to_edit"), int)
                or st.session_state["favorite_to_edit"] not in favorites_by_id
            ):
                st.session_state.pop("favorite_to_edit", None)
            selected_favorite_id = st.selectbox(
                "Favorito para organizar",
                list(favorites_by_id),
                format_func=lambda favorite_id: _favorite_label(
                    favorites_by_id[favorite_id], equipment_by_id, experiments_by_id
                ),
                key="favorite_to_edit",
            )
            selected_favorite = favorites_by_id[selected_favorite_id]
            with st.form("move_favorite"):
                selected_folder_id = st.selectbox(
                    "Mover para",
                    [None, *[folder.id for folder in folders]],
                    index=(
                        [None, *[folder.id for folder in folders]].index(
                            selected_favorite.folder_id
                        )
                        if selected_favorite.folder_id
                        in [None, *[folder.id for folder in folders]]
                        else 0
                    ),
                    format_func=lambda folder_id: (
                        "Sem pasta" if folder_id is None else folder_names[folder_id]
                    ),
                )
                submitted = st.form_submit_button("Salvar organização")
            if submitted:
                selected_favorite.folder_id = selected_folder_id
                if _commit(session, "Favorito atualizado."):
                    st.rerun()
    with remove_favorite:
        if not favorites:
            st.info("Você ainda não tem favoritos.")
        else:
            favorites_by_id = {item.id: item for item in favorites}
            if (
                not isinstance(st.session_state.get("favorite_to_remove"), int)
                or st.session_state["favorite_to_remove"] not in favorites_by_id
            ):
                st.session_state.pop("favorite_to_remove", None)
            selected_favorite_id = st.selectbox(
                "Favorito",
                list(favorites_by_id),
                format_func=lambda favorite_id: _favorite_label(
                    favorites_by_id[favorite_id],
                    equipment_by_id,
                    experiments_by_id,
                ),
                key="favorite_to_remove",
            )
            selected_favorite = favorites_by_id[selected_favorite_id]
            with st.form("remove_favorite"):
                confirm = st.checkbox("Confirmo a remoção deste favorito")
                delete = st.form_submit_button("Remover favorito")
            if delete:
                if not confirm:
                    st.error("Confirme a remoção antes de continuar.")
                else:
                    session.delete(selected_favorite)
                    if _commit(session, "Favorito removido."):
                        st.rerun()


def _favorite_label(
    favorite: Favorite,
    equipment: dict[int, Equipment],
    experiments: dict[int, Experiment],
) -> str:
    if favorite.equipment_id is not None:
        item = equipment.get(favorite.equipment_id)
        return item.name if item else "Equipamento removido"
    item = experiments.get(favorite.experiment_id)
    return item.title if item else "Experimento removido"


def _profile_page(session: Session, user: User) -> None:
    st.title("Meu perfil")
    st.write(f"**E-mail:** {user.email}")
    st.write(f"**Perfil:** {'Docente' if user.role == 'teacher' else 'Discente'}")
    with st.form("profile_form"):
        full_name = st.text_input("Nome completo", value=user.full_name)
        current_password = st.text_input("Senha atual", type="password")
        new_password = st.text_input("Nova senha (opcional)", type="password")
        submitted = st.form_submit_button("Atualizar perfil", type="primary")
    if submitted:
        if not full_name.strip():
            st.error("Informe seu nome.")
        elif new_password and not verify_password(
            current_password, user.password_hash
        ):
            st.error("A senha atual está incorreta.")
        elif new_password and len(new_password) < 10:
            st.error("A nova senha deve ter pelo menos 10 caracteres.")
        else:
            user.full_name = full_name.strip()
            if new_password:
                user.password_hash = hash_password(new_password)
            if _commit(session, "Perfil atualizado."):
                st.rerun()

    st.divider()
    with st.expander("Excluir minha conta"):
        st.warning(
            "A exclusão remove seu perfil, suas pastas e seus favoritos. "
            "Os experimentos cadastrados por você serão mantidos."
        )
        with st.form("delete_account"):
            confirmation = st.text_input("Digite seu e-mail para confirmar")
            delete = st.form_submit_button("Excluir conta")
        if delete:
            if confirmation.strip().lower() != user.email:
                st.error("O e-mail informado não corresponde à sua conta.")
            else:
                session.delete(user)
                if _commit(session, "Conta excluída."):
                    st.session_state.pop("user_id", None)
                    st.rerun()


def _load_application(engine: Engine) -> None:
    try:
        initialize_database(engine)
    except SQLAlchemyError as error:
        st.error(
            "Não foi possível inicializar o banco de dados. "
            f"Confira a conexão e o esquema. ({type(error).__name__})"
        )
        st.stop()


def main() -> None:
    st.set_page_config(
        page_title="Organizador de Laboratório · IFC Blumenau",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .stApp { background: #f5f7fb; }
        [data-testid="stSidebar"] { background: #102a43; }
        [data-testid="stSidebar"] * { color: #f5f7fb; }
        [data-testid="stMetric"] {
            background: white; padding: 1rem; border-radius: 0.8rem;
            border: 1px solid #e3eaf2;
        }
        div[data-testid="stForm"] {
            background: white; padding: 1rem; border-radius: 0.8rem;
            border: 1px solid #e3eaf2;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    try:
        engine = get_engine()
    except RuntimeError as error:
        st.error(str(error))
        st.stop()
    _load_application(engine)

    with Session(engine) as session:
        user_id = st.session_state.get("user_id")
        if user_id is None:
            _auth_screen(session)
            return

        user = session.get(User, user_id)
        if user is None:
            st.session_state.pop("user_id", None)
            st.error("Sua sessão não corresponde a uma conta ativa.")
            st.rerun()

        with st.sidebar:
            st.markdown("## ⚡ OLAF")
            st.caption("Organizador de Laboratório de Física")
            st.write(user.full_name)
            st.caption("Docente" if user.role == "teacher" else "Discente")
            page = st.radio(
                "Navegação",
                ("Início", "Equipamentos", "Experimentos", "Pastas e favoritos", "Perfil"),
            )
            if st.button("Sair", width="stretch"):
                st.session_state.pop("user_id", None)
                st.rerun()

        page_handlers: dict[str, Callable[[Session, User], None]] = {
            "Início": _dashboard,
            "Equipamentos": _equipment_page,
            "Experimentos": _experiment_page,
            "Pastas e favoritos": _folder_page,
            "Perfil": _profile_page,
        }
        page_handlers[page](session, user)


if __name__ == "__main__":
    main()
