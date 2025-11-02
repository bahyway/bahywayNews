import { GetServerSideProps } from 'next';
import { useRouter } from 'next/router';

interface UserProfile {
    id: number;
    email: string;
    full_name: string;
    bio: string;
}

interface ProfilePageProps {
    profile: UserProfile | null;
}

const ProfilePage = ({ profile }: ProfilePageProps) => {
    const router = useRouter();

    if (router.isFallback) {
        return <div>Loading...</div>;
    }

    if (!profile) {
        return <div>Profile not found.</div>;
    }

    return (
        <div>
            <h1>{profile.full_name}</h1>
            <p>Email: {profile.email}</p>
            <p>{profile.bio}</p>
        </div>
    );
};

export const getServerSideProps: GetServerSideProps = async (context) => {
    const { id } = context.params!;
    try {
        // This URL points to our Kubernetes Ingress, which routes to the service
        const res = await fetch(`http://bahyway.local/api/users/${id}`);
        if (!res.ok) {
            return { props: { profile: null } };
        }
        const profile: UserProfile = await res.json();
        return { props: { profile } };
    } catch (error) {
        console.error("Failed to fetch profile", error);
        return { props: { profile: null } };
    }
};

export default ProfilePage;
